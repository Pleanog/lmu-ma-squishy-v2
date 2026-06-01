#!/usr/bin/env python3
"""
Simple USB Microphone Test
Quick test to check if microphone works
"""

import pyaudio
import numpy as np
import sys

def quick_test():
    """Quick microphone test"""
    p = pyaudio.PyAudio()
    
    print("\n📻 USB Microphone Quick Test")
    print("=" * 50)
    
    # List devices
    print("\nAvailable input devices:")
    input_devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            input_devices.append(i)
            marker = "📌 (default)" if i == p.get_default_input_device_info()['index'] else ""
            print(f"  {i}: {info['name']} {marker}")
    
    if not input_devices:
        print("\n❌ No input devices found!")
        p.terminate()
        return False
    
    # Choose device
    while True:
        choice = input(f"\nSelect device (0-{len(input_devices)-1}, or Enter for default): ").strip()
        if choice == "":
            device = input_devices[0]
            break
        if choice.isdigit() and int(choice) in input_devices:
            device = int(choice)
            break
        print("Invalid choice!")
    
    # Test recording
    print(f"\n🎤 Recording from device {device}...")
    print("Speak into microphone for 5 seconds...")
    
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=device,
            frames_per_buffer=1024
        )
        
        max_level = 0
        for i in range(80):  # ~5 seconds at 16kHz
            data = stream.read(1024, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.int16)
            level = int((np.sqrt(np.mean(audio ** 2)) / 32767) * 100)
            max_level = max(max_level, level)
            
            bar = "█" * (level // 5)
            print(f"  [{i+1:2d}/80] {bar:<20} {level:3d}%")
        
        stream.stop_stream()
        stream.close()
        
        print(f"\n✅ Max audio level: {max_level}%")
        
        if max_level < 5:
            print("⚠️  Audio level is very low! Check microphone connection.")
        elif max_level < 20:
            print("⚠️  Audio level is low. Microphone may be too far or quiet.")
        else:
            print("✅ Microphone is working well!")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    finally:
        p.terminate()

if __name__ == "__main__":
    try:
        success = quick_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled")
        sys.exit(1)
