import pandas as pd
import numpy as np
import re
from typing import Dict, Any, List, Optional
from src.core.forecaster import ProductForecaster
from src.utils.logger import setup_logger

logger = setup_logger("simulator")

class ScenarioSimulator:
    def __init__(self, forecaster: ProductForecaster):
        self.forecaster = forecaster

    def simulate_what_if(
        self,
        historical_df: pd.DataFrame,
        product_id: str,
        horizon_days: int,
        target_metric: str,
        modifications: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Simulates changes to variables (e.g. Marketing_Spend, Discount_Pct, Shipping_Fee)
        and measures their impact on a forecast target metric.
        
        modifications format:
        {
            "Discount_Pct": {"type": "add", "value": 0.05},
            "Shipping_Fee": {"type": "multiply", "value": 1.10}
        }
        """
        target_metric_cap = target_metric.title()
        if target_metric_cap not in self.forecaster.models:
            matched = [t for t in self.forecaster.models.keys() if t.lower() == target_metric.lower()]
            if matched:
                target_metric_cap = matched[0]
            else:
                raise ValueError(f"Target metric {target_metric} not supported.")
                
        # 1. Run Baseline Forecast
        baseline_forecast = self.forecaster.forecast(
            historical_df=historical_df,
            product_id=product_id,
            horizon_days=horizon_days,
            future_overrides=None
        )
        
        # 2. Extract baseline values for the modified variables to apply offsets
        # For simplicity, extract the defaults that would be used (i.e. last known historical values)
        prod_data = historical_df[historical_df["product_id"] == product_id].copy()
        prod_data["date"] = pd.to_datetime(prod_data["date"])
        prod_data = prod_data.sort_values(by="date").reset_index(drop=True)
        
        last_history = prod_data.tail(1).iloc[0]
        
        # 3. Build future overrides dictionary
        future_overrides = {}
        for var, mod in modifications.items():
            mod_type = mod.get("type", "set")
            mod_val = mod.get("value", 0.0)
            
            # Get base value
            if var in last_history:
                base_val = last_history[var]
            else:
                base_val = 0.0
                
            # Apply transformation
            future_list = []
            for _ in range(horizon_days):
                if mod_type == "add":
                    val = base_val + mod_val
                elif mod_type == "multiply":
                    val = base_val * mod_val
                elif mod_type == "set":
                    val = mod_val
                else:
                    val = base_val
                    
                # Boundary bounds
                if var == "discount_pct":
                    val = max(0.0, min(100.0, val))
                elif var in ["marketing_spend", "shipping_fee"] and val < 0:
                    val = 0.0
                    
                future_list.append(val)
                
            future_overrides[var] = future_list
            
        # 4. Run Simulated Forecast
        simulated_forecast = self.forecaster.forecast(
            historical_df=historical_df,
            product_id=product_id,
            horizon_days=horizon_days,
            future_overrides=future_overrides
        )
        
        # 5. Compute comparisons
        base_vals = baseline_forecast[target_metric_cap].values
        sim_vals = simulated_forecast[target_metric_cap].values
        dates = baseline_forecast["date"].dt.strftime("%Y-%m-%d").values
        
        baseline_sum = float(np.sum(base_vals))
        simulated_sum = float(np.sum(sim_vals))
        abs_diff = simulated_sum - baseline_sum
        
        pct_diff = (abs_diff / baseline_sum * 100.0) if baseline_sum != 0 else 0.0
        
        impact = "neutral"
        if abs_diff > 1e-4:
            impact = "positive"
        elif abs_diff < -1e-4:
            impact = "negative"
            
        daily_comparison = []
        for d, b, s in zip(dates, base_vals, sim_vals):
            daily_comparison.append({
                "date": d,
                "baseline_value": float(b),
                "simulated_value": float(s),
                "difference": float(s - b)
            })
            
        return {
            "target_metric": target_metric,
            "product_id": product_id,
            "horizon_days": horizon_days,
            "modifications": modifications,
            "baseline_sum": round(baseline_sum, 2),
            "simulated_sum": round(simulated_sum, 2),
            "absolute_difference": round(abs_diff, 2),
            "percentage_difference": round(pct_diff, 2),
            "impact": impact,
            "daily_comparison": daily_comparison
        }

    def parse_change_string(self, change_str: str) -> Optional[tuple]:
        """
        Parses a scenario change string like 'discount +5%', 'marketing +10%', 'shipping +20'
        Returns a tuple of (variable_name, mod_type, value) or None.
        """
        s = change_str.strip().lower()
        
        var_map = {
            "discount": "discount_pct",
            "marketing": "marketing_spend",
            "shipping": "shipping_fee",
            "price": "avg_selling_price",
            "inventory": "inventory_available",
            "traffic": "traffic"
        }
        
        matched_prefix = None
        for prefix in var_map.keys():
            if s.startswith(prefix):
                matched_prefix = prefix
                break
                
        if not matched_prefix:
            return None
            
        var_name = var_map[matched_prefix]
        rest = s[len(matched_prefix):].strip()
        
        # Match operator and value
        match = re.match(r"^(=|\+|-)?\s*([0-9]+(?:\.[0-9]+)?)\s*(%)?$", rest)
        if not match:
            # Try without operator
            match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(%)?$", rest)
            if match:
                op = "="
                val_str = match.group(1)
                is_pct = bool(match.group(2))
            else:
                return None
        else:
            op = match.group(1) or "="
            val_str = match.group(2)
            is_pct = bool(match.group(3))
            
        val = float(val_str)
        
        if op == "=":
            return var_name, "set", val
        elif op == "+":
            if is_pct:
                return var_name, "multiply", 1.0 + (val / 100.0)
            else:
                return var_name, "add", val
        elif op == "-":
            if is_pct:
                return var_name, "multiply", 1.0 - (val / 100.0)
            else:
                return var_name, "add", -val
                
        return None

    def evaluate_scenario(
        self,
        historical_df: pd.DataFrame,
        product_id: str,
        horizon_days: int,
        changes: List[str],
        current_features: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates the joint impact of a list of scenario change strings on all 5 predicted KPIs:
        Revenue, Profit, Orders, Conversion, Retention.
        """
        # 1. Parse all change strings
        modifications = {}
        for change in changes:
            parsed = self.parse_change_string(change)
            if parsed:
                var_name, mod_type, value = parsed
                modifications[var_name] = {"type": mod_type, "value": value}
            else:
                logger.warning(f"Failed to parse change string: {change}")
                
        # 2. Run Baseline Forecast
        baseline_forecast = self.forecaster.forecast(
            historical_df=historical_df,
            product_id=product_id,
            horizon_days=horizon_days,
            future_overrides=None,
            current_features=current_features
        )
        
        # 3. Extract baseline values to apply offsets
        prod_data = historical_df[historical_df["product_id"] == product_id].copy()
        prod_data["date"] = pd.to_datetime(prod_data["date"])
        prod_data = prod_data.sort_values(by="date").reset_index(drop=True)
        
        last_history_row = prod_data.tail(1).copy()
        if current_features:
            for key, val in current_features.items():
                key_lower = key.lower()
                if key_lower == "price":
                    key_lower = "avg_selling_price"
                elif key_lower == "inventory":
                    key_lower = "inventory_available"
                if key_lower in last_history_row.columns:
                    last_history_row[key_lower] = val
                    
        last_history = last_history_row.iloc[0]
        
        # 4. Build future overrides dictionary
        future_overrides = {}
        for var, mod in modifications.items():
            mod_type = mod.get("type", "set")
            mod_val = mod.get("value", 0.0)
            
            if var in last_history:
                base_val = last_history[var]
            else:
                base_val = 0.0
                
            future_list = []
            for _ in range(horizon_days):
                if mod_type == "add":
                    val = base_val + mod_val
                elif mod_type == "multiply":
                    val = base_val * mod_val
                elif mod_type == "set":
                    val = mod_val
                else:
                    val = base_val
                    
                # Boundary bounds
                if var == "discount_pct":
                    val = max(0.0, min(100.0, val))
                elif var in ["marketing_spend", "shipping_fee"] and val < 0:
                    val = 0.0
                    
                future_list.append(val)
                
            future_overrides[var] = future_list
            
        # 5. Run Simulated Forecast
        simulated_forecast = self.forecaster.forecast(
            historical_df=historical_df,
            product_id=product_id,
            horizon_days=horizon_days,
            future_overrides=future_overrides,
            current_features=current_features
        )
        
        # 6. Aggregates results for all 5 target KPIs
        targets = ["revenue", "profit", "orders", "conversion_rate", "retention_rate"]
        kpi_summaries = {}
        daily_comparison = {}
        
        dates = baseline_forecast["date"].dt.strftime("%Y-%m-%d").values
        
        for target in targets:
            base_vals = baseline_forecast[target].values
            sim_vals = simulated_forecast[target].values
            
            is_rate = target in ["conversion_rate", "retention_rate"]
            
            if is_rate:
                baseline_agg = float(np.mean(base_vals))
                simulated_agg = float(np.mean(sim_vals))
            else:
                baseline_agg = float(np.sum(base_vals))
                simulated_agg = float(np.sum(sim_vals))
                
            abs_diff = simulated_agg - baseline_agg
            pct_diff = (abs_diff / baseline_agg * 100.0) if baseline_agg != 0 else 0.0
            
            impact = "neutral"
            if abs_diff > 1e-6:
                impact = "positive"
            elif abs_diff < -1e-6:
                impact = "negative"
                
            kpi_summaries[target] = {
                "baseline": round(baseline_agg, 4),
                "simulated": round(simulated_agg, 4),
                "absolute_difference": round(abs_diff, 4),
                "percentage_difference": round(pct_diff, 2),
                "impact": impact
            }
            
            # Populate daily points
            target_daily = []
            for d, b, s in zip(dates, base_vals, sim_vals):
                target_daily.append({
                    "date": d,
                    "baseline_value": float(b),
                    "simulated_value": float(s),
                    "difference": float(s - b)
                })
            daily_comparison[target] = target_daily
            
        return {
            "product_id": product_id,
            "horizon_days": horizon_days,
            "changes": changes,
            "kpis": kpi_summaries,
            "daily_comparison": daily_comparison
        }
