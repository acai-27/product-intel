import argparse
from anomaly_detect.service import detect_anomalies

def main():
    parser = argparse.ArgumentParser(description="Run Anomaly Detection POC locally.")
    parser.add_argument("--product_id", type=str, default="P001", help="Product ID to analyze")
    parser.add_argument("--kpi", type=str, default="revenue", help="KPI to analyze")
    parser.add_argument("--date_range", type=str, default="180 Days", help="Date Range")
    parser.add_argument("--file_path", type=str, default="temporal_dataset.csv", help="Path to historical dataset")
    
    args = parser.parse_args()
    
    print(f"Running anomaly detection for Product: {args.product_id}, KPI: {args.kpi}, Range: {args.date_range}")
    
    try:
        result = detect_anomalies(
            file_path=args.file_path,
            product_id=args.product_id,
            kpi=args.kpi,
            date_range=args.date_range
        )
        
        print(f"\n--- Anomaly Summary ---")
        print(f"Product ID: {result.product_id}")
        print(f"KPI: {result.kpi}")
        print(f"Threshold Method: {result.summary.threshold_method.capitalize()}")
        print(f"Threshold Percentile: {result.summary.threshold_percentile}")
        print(f"Threshold Score: {result.summary.threshold_value}")
        print(f"Total Points Displayed: {result.summary.total_points}")
        print(f"Total Anomalies: {result.summary.anomaly_count}")
        print(f"Positive Spikes: {result.summary.positive_anomalies}")
        print(f"Negative Drops: {result.summary.negative_anomalies}")
        
        print("\n--- Detected Anomalies ---")
        for p in result.anomalies:
            print(f"Date: {p.date} | Value: {p.value} | Type: {p.anomaly_type} | Status: {p.status} | Score: {p.score}")
                
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    main()
