# EA-WIP: Ergonomic Calibration and Occlusion-Aware Speed Estimation for Personalized Vision-Based Walking-in-Place

Camera-based VR locomotion with user-specific calibration and occlusion-aware speed estimation.

## Overview

EA-WIP is a vision-based Walking-In-Place (WIP) algorithm that estimates virtual walking speed by combining:
- **Stride amplitude and cadence integration** (Eq. 10-11)
- **Visibility-weighted aggregation** (Eq. 12)
- **Occlusion-aware suppression** (Eq. 13-16)
- **User-specific calibration** (Eq. 3-9)

This implementation uses a single RGB camera and MediaPipe Pose for markerless motion tracking.

## Features

- ✅ **No specialized hardware required** - Single webcam only
- ✅ **Personalized calibration** - Adapts to individual gait patterns
- ✅ **Occlusion handling** - Robust to partial visibility loss
- ✅ **Real-time performance** - ~30 FPS on CPU
- ✅ **Unity integration** - UDP communication for VR environments

## Installation

### Requirements
- Python 3.8+
- Webcam
- (Optional) Unity project for VR visualization

### Setup
```bash
# Clone repository
git clone https://github.com/yourusername/EA-WIP.git
cd EA-WIP

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
python main.py
```

### Custom Configuration
```bash
python main.py --udp-ip 192.168.1.100 --udp-port 5005 --camera-id 0 --base-speed 1.3
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--udp-ip` | str | 127.0.0.1 | UDP target IP address |
| `--udp-port` | int | 5005 | UDP target port |
| `--camera-id` | int | 0 | Camera device ID |
| `--base-speed` | float | 1.3 | Base walking speed v0 (m/s) |

## Project Structure
```
EA-WIP/
├── core/                   # Algorithm implementation
│   ├── calibration.py      # Calibration logic (Eq. 3-9)
│   └── ea_wip.py          # EA-WIP algorithm (Eq. 10-16)
│
├── vision/                 # Computer vision
│   └── pose_estimator.py  # MediaPipe wrapper
│
├── communication/          # Network communication
│   └── udp_client.py      # UDP client/receiver
│
├── ui/                     # User interface
│   ├── calibration_window.py
│   └── inference_window.py
│
├── utils/                  # Utilities
│   └── config.py          # Configuration management
│
└── main.py                # Entry point
```

## Algorithm Overview

### Calibration Phase (8 seconds)

The system computes user-specific baselines:

1. **Ground Reference** (Eq. 3): Minimum ankle height over 2s windows
2. **Variability** (Eq. 4): Standard deviation of ankle height
3. **Step Detection Threshold** (Eq. 5): `T = μ_h + 0.5σ_h`
4. **Stride Amplitude Baseline** (Eq. 7): Average vertical excursion per step
5. **Cadence Baseline** (Eq. 9): Natural stepping frequency

### Runtime Estimation

The algorithm estimates speed using:

**Stride-Cadence Index** (Eq. 10-11):
```
r_h = h / h_c
r_f = f / f_c
z = √(r_h × r_f)
```

**Visibility-Weighted Speed** (Eq. 12):
```
v* = v0 / (V_L + V_R) × [V_L × z_L + V_R × z_R]
```

### Occlusion Handling

**Occlusion Confidence Index** (Eq. 13-16):
```
ΔV_i = V̄_i - V_i(t)
σ_V_i = std(V_i)
OCI_i = ΔV_i + λσ_V_i
```

Speed updates are suppressed when `OCI_mean > θ_o` (0.25).

## Unity Integration

The system sends speed data via UDP:
```
Format: "speed,frame,frequency,h_left,h_right,warning"
Example: "1.2500,150,1.80,0.1200,0.1150,0"
```

### Unity Receiver (C#)
```csharp
UdpClient udpClient = new UdpClient(5005);
IPEndPoint remoteEP = new IPEndPoint(IPAddress.Any, 5005);

byte[] data = udpClient.Receive(ref remoteEP);
string message = Encoding.UTF8.GetString(data);
string[] values = message.Split(',');

float speed = float.Parse(values[0]);
// Apply to VR character controller
```

## Parameters

### Algorithm Parameters (from paper)

| Parameter | Symbol | Value | Description |
|-----------|--------|-------|-------------|
| Base speed | v0 | 1.3 m/s | Average adult walking speed |
| Lambda | λ | 0.5 | OCI visibility fluctuation weight |
| Theta | θ_o | 0.25 | OCI suppression threshold |
| Window size | T | 2.0 s | Visibility history window |

### Calibration Parameters

| Parameter | Symbol | Unit | Description |
|-----------|--------|------|-------------|
| Ground reference | μ_h | m | Stance-phase ankle height |
| Variability | σ_h | m | Ankle height std. dev. |
| Detection threshold | T | m | Step event trigger |
| Stride amplitude | h_c | m | Baseline vertical excursion |
| Cadence | f_c | Hz | Baseline step frequency |

## Troubleshooting

### Camera Issues
- Ensure webcam is connected and not in use by other applications
- Try different `--camera-id` values (0, 1, 2...)

### Pose Detection Issues
- Ensure good lighting conditions
- Stand 2-3 meters from camera
- Wear contrasting clothing

### UDP Connection Issues
- Check firewall settings
- Verify Unity is listening on correct port
- Use `--udp-ip` to specify correct network interface

## License

MIT License - See LICENSE file for details

## Acknowledgments

- MediaPipe Pose by Google Research
- Paper equations reference: Section III-C through III-E
