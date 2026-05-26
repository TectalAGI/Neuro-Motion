#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <mujoco.h>

struct SensorFrame {
    double time;
    double ax, ay, az;
    double abs_accel;
};

std::vector<SensorFrame> parsePhyphox(const std::string& filepath) {
    std::vector<SensorFrame> frames;
    std::ifstream file(filepath);
    std::string line;
    std::getline(file, line);
    while (std::getline(file, line)) {
        std::istringstream ss(line);
        SensorFrame f;
        char tab;
        ss >> f.time >> tab >> f.ax >> tab >> f.ay >> tab >> f.az >> tab >> f.abs_accel;
        frames.push_back(f);
    }
    return frames;
}

int main() {
    // Load MuJoCo arm model
    char error[1000];
    mjModel* model = mj_loadXML("/Users/aj/Neuro-Motion/mujoco_arm_demo/arm.xml", nullptr, error, 1000);
    if (!model) {
        std::cerr << "Failed to load model: " << error << std::endl;
        return 1;
    }
    mjData* data = mj_makeData(model);
    std::cout << "Model loaded! Joints: " << model->njnt << std::endl;

    // Load Phyphox data
    auto frames = parsePhyphox("/Users/aj/Downloads/Acceleration with g 2026-05-25 22-51-31/JayceArmData1.csv");
    std::cout << "Loaded " << frames.size() << " sensor frames" << std::endl;
    std::cout << "First frame: t=" << frames[0].time << " abs_accel=" << frames[0].abs_accel << std::endl;

    // LIF spike detection
    double voltage = 0.0;
    double decay = 0.5;
    double threshold = 20.0;
    double reset = 0.0;

    std::cout << "\n--- Detected Snaps ---" << std::endl;
    int snap_count = 0;

    for (const auto& frame : frames) {
        voltage += frame.abs_accel;
        voltage *= decay;

        if (voltage > threshold) {
            std::cout << "SNAP at t=" << frame.time
                      << "s | acceleration=" << frame.abs_accel
                      << " m/s^2" << std::endl;
            voltage = reset;
            snap_count++;
        }
    }

    std::cout << "\nTotal snaps detected: " << snap_count << std::endl;

    // Cleanup
    mj_deleteData(data);
    mj_deleteModel(model);
    return 0;
}