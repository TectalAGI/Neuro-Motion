#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

struct SensorFrame {
    double time;
    double ax;
    double ay;
    double az;
    double abs_accel;
};

struct SnapFrame {
    double time;
    double ax;
    double ay;
    double az;
    double abs_accel;
    double voltage;
    int snap;
    int cumulative_snaps;
};

std::vector<SensorFrame> parsePhyphox(const std::string& filepath) {
    std::vector<SensorFrame> frames;
    std::ifstream file(filepath);
    std::string line;
    std::getline(file, line);

    while (std::getline(file, line)) {
        if (line.empty()) {
            continue;
        }

        std::istringstream ss(line);
        std::string token;
        SensorFrame frame{};

        std::getline(ss, token, ',');
        frame.time = std::stod(token);
        std::getline(ss, token, ',');
        frame.ax = std::stod(token);
        std::getline(ss, token, ',');
        frame.ay = std::stod(token);
        std::getline(ss, token, ',');
        frame.az = std::stod(token);
        std::getline(ss, token, ',');
        frame.abs_accel = std::stod(token);
        frames.push_back(frame);
    }

    return frames;
}

std::vector<SnapFrame> detectSnaps(
    const std::vector<SensorFrame>& frames,
    double decay = 0.5,
    double threshold = 20.0,
    double reset = 0.0
) {
    std::vector<SnapFrame> results;
    results.reserve(frames.size());

    double voltage = 0.0;
    int snap_count = 0;

    for (const auto& frame : frames) {
        voltage += frame.abs_accel;
        voltage *= decay;

        bool snap = voltage > threshold;
        double snap_voltage = voltage;
        if (snap) {
            ++snap_count;
            voltage = reset;
        }

        results.push_back(
            SnapFrame{
                frame.time,
                frame.ax,
                frame.ay,
                frame.az,
                frame.abs_accel,
                snap_voltage,
                snap ? 1 : 0,
                snap_count,
            }
        );
    }

    return results;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " path/to/phyphox.csv\n";
        return 1;
    }

    auto frames = parsePhyphox(argv[1]);
    if (frames.empty()) {
        std::cerr << "No sensor frames parsed from " << argv[1] << "\n";
        return 2;
    }

    auto results = detectSnaps(frames);

    std::cout << "time,ax,ay,az,abs_accel,voltage,snap,cumulative_snaps\n";
    std::cout << std::fixed << std::setprecision(9);
    for (const auto& frame : results) {
        std::cout << frame.time << ","
                  << frame.ax << ","
                  << frame.ay << ","
                  << frame.az << ","
                  << frame.abs_accel << ","
                  << frame.voltage << ","
                  << frame.snap << ","
                  << frame.cumulative_snaps << "\n";
    }

    return 0;
}
