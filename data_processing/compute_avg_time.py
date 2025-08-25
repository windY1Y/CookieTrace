import json
import sys
from collections import defaultdict

def calculate_metric_averages(data):
    metric_sums = defaultdict(list)
    
    for site, metrics in data.items():
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                metric_sums[key].append(value)
    
    averages = {}
    for metric, values in metric_sums.items():
        if values:
            averages[metric] = sum(values) / len(values)
    
    return averages

def main():
    input_data = sys.stdin.read()
    
    try:
        data = json.loads(input_data)
        
        averages = calculate_metric_averages(data)
        
        print("average:")
        for metric, avg in averages.items():
            print(f"{metric}: {avg:.6f}")
        
    except json.JSONDecodeError as e:
        print(f"JSON error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()