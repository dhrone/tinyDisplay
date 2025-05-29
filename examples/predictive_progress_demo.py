#!/usr/bin/env python3
"""
Predictive Progress Bar Demo

Demonstrates the new predictive progress functionality that estimates
progress between data updates using historical rate calculation.

This is particularly useful for scenarios like:
- File downloads with intermittent progress updates
- Data processing with variable update intervals
- Network operations with unpredictable timing
"""

import time
import random
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.tinydisplay.widgets.progress import (
    ProgressBarWidget, ProgressPrediction, ProgressStyle
)
from src.tinydisplay.widgets.base import ReactiveValue


def simulate_file_download():
    """Simulate a file download with predictive progress."""
    print("🚀 Predictive Progress Bar Demo")
    print("=" * 50)
    
    # Create predictive progress configuration
    prediction = ProgressPrediction(
        enabled=True,
        min_samples=3,           # Need 3 data points for prediction
        max_prediction_time=5.0, # Predict up to 5 seconds ahead
        confidence_decay_rate=0.8, # Confidence decays 20% per second
        rate_smoothing=0.7       # Smooth rate changes by 70%
    )
    
    # Create progress bar with prediction enabled
    progress_bar = ProgressBarWidget(
        progress=0.0,
        prediction=prediction,
        min_value=0.0,
        max_value=100.0  # Progress in percentage
    )
    
    print(f"📊 Created progress bar with predictive capabilities")
    print(f"   Min samples: {prediction.min_samples}")
    print(f"   Max prediction time: {prediction.max_prediction_time}s")
    print(f"   Rate smoothing: {prediction.rate_smoothing}")
    print()
    
    # Simulate download progress with irregular updates
    download_progress = 0.0
    download_rate = 5.0  # Base rate: 5% per second
    
    print("📥 Starting simulated download...")
    print("Time | Actual | Predicted | Rate | Confidence | Status")
    print("-" * 60)
    
    start_time = time.time()
    last_update = start_time
    
    for i in range(15):  # 15 iterations
        current_time = time.time()
        elapsed = current_time - start_time
        
        # Simulate irregular update intervals (0.5 to 2.5 seconds)
        if current_time - last_update >= random.uniform(0.5, 2.5):
            # Update actual progress
            time_delta = current_time - last_update
            # Add some randomness to download rate
            actual_rate = download_rate * random.uniform(0.7, 1.3)
            download_progress += actual_rate * time_delta
            download_progress = min(100.0, download_progress)
            
            # Update progress bar
            progress_bar.progress = download_progress
            last_update = current_time
            
            # Get prediction info
            info = progress_bar.get_prediction_info()
            
            print(f"{elapsed:4.1f}s | {download_progress:6.1f}% | "
                  f"{progress_bar.animated_progress*100:8.1f}% | "
                  f"{info['rate']*100 if info['rate'] else 0:4.1f}%/s | "
                  f"{info['confidence']:8.1f} | "
                  f"{'PREDICTING' if info['is_predicting'] else 'ACTUAL'}")
        else:
            # Show predicted progress between updates
            info = progress_bar.get_prediction_info()
            predicted = progress_bar.animated_progress * 100
            
            print(f"{elapsed:4.1f}s | {download_progress:6.1f}% | "
                  f"{predicted:8.1f}% | "
                  f"{info['rate']*100 if info['rate'] else 0:4.1f}%/s | "
                  f"{info['confidence']:8.1f} | "
                  f"{'PREDICTING' if info['is_predicting'] else 'WAITING'}")
        
        if download_progress >= 100.0:
            print("\n✅ Download complete!")
            break
        
        time.sleep(0.3)  # Update display every 300ms
    
    print()
    print("📈 Final Prediction Statistics:")
    final_info = progress_bar.get_prediction_info()
    print(f"   Samples collected: {final_info['samples_count']}")
    print(f"   Final rate: {final_info['rate']*100 if final_info['rate'] else 0:.1f}%/s")
    print(f"   Final confidence: {final_info['confidence']:.2f}")


def demonstrate_prediction_features():
    """Demonstrate various prediction features."""
    print("\n🔬 Prediction Features Demo")
    print("=" * 50)
    
    # Create progress bar with custom prediction settings
    prediction = ProgressPrediction(
        enabled=True,
        min_samples=2,
        max_samples=5,
        max_prediction_time=3.0,
        confidence_decay_rate=0.9,
        rate_smoothing=0.5
    )
    
    progress_bar = ProgressBarWidget(0.0, prediction=prediction)
    
    print("📊 Testing prediction configuration...")
    
    # Test 1: Insufficient samples
    print(f"1. Initial state (no samples): {progress_bar.is_predicting}")
    
    # Test 2: Add samples and check prediction
    progress_bar.progress = 0.1
    time.sleep(0.1)
    progress_bar.progress = 0.2
    print(f"2. After 2 samples: {progress_bar.is_predicting}")
    
    # Test 3: Check prediction info
    info = progress_bar.get_prediction_info()
    print(f"3. Prediction info:")
    for key, value in info.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.3f}")
        else:
            print(f"   {key}: {value}")
    
    # Test 4: Disable and re-enable prediction
    progress_bar.enable_prediction(False)
    print(f"4. After disabling: {progress_bar.is_predicting}")
    
    progress_bar.enable_prediction(True, max_prediction_time=10.0)
    print(f"5. After re-enabling: {progress_bar.is_predicting}")
    
    # Test 5: Clear history
    progress_bar.clear_prediction_history()
    print(f"6. After clearing history: {progress_bar.is_predicting}")


if __name__ == "__main__":
    try:
        simulate_file_download()
        demonstrate_prediction_features()
        
        print("\n🎉 Demo completed successfully!")
        print("\nKey Benefits of Predictive Progress:")
        print("• Smoother user experience with estimated progress")
        print("• Reduces perceived waiting time")
        print("• Confidence-based blending ensures accuracy")
        print("• Configurable parameters for different use cases")
        print("• Graceful fallback when predictions aren't reliable")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        raise 