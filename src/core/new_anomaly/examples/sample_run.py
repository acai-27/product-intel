import os
import sys

# Add the parent directory to the path so we can import anomaly_detect
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from anomaly_detect.service import detect_anomalies

def run_example():
    print("Loading product P002, finding revenue anomalies over the last 90 days...")
    
    dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "temporal_dataset.csv")
    
    result = detect_anomalies(
        file_path=dataset_path,
        product_id="P002",
        kpi="revenue",
        date_range="90 Days"
    )
    
    print(f"\n--- Anomaly Summary ---")
    print(f"Total Points: {result.summary.total_points}")
    print(f"Anomaly Count: {result.summary.anomaly_count}")
    print(f"Positive Spikes: {result.summary.positive_anomalies}")
    print(f"Negative Drops: {result.summary.negative_anomalies}")
    print(f"Threshold Method: {result.summary.threshold_method.capitalize()}")
    print(f"Threshold Percentile: {result.summary.threshold_percentile}")
    print(f"Threshold Score: {result.summary.threshold_value}")
    
    print("\n--- Detected Anomalies ---")
    for point in result.anomalies:
        print(f"Date: {point.date} | Revenue: {point.value} | Type: {point.anomaly_type} | Status: {point.status} | Score: {point.score}")

if __name__ == "__main__":
    run_example()
