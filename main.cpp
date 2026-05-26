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

struct SnapEvent {
    double time;
    double acceleration;
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
    double reset_val = 0.0;

    std::vector<SnapEvent> snaps;

    for (const auto& frame : frames) {
        voltage += frame.abs_accel;
        voltage *= decay;

        if (voltage > threshold) {
            snaps.push_back({frame.time, frame.abs_accel});
            voltage = reset_val;
        }
    }

    // Print snaps
    std::cout << "\n--- Detected Snaps ---" << std::endl;
    for (const auto& snap : snaps) {
        std::cout << "SNAP at t=" << snap.time
                  << "s | acceleration=" << snap.acceleration
                  << " m/s^2" << std::endl;
    }
    std::cout << "\nTotal snaps detected: " << snaps.size() << std::endl;

    // Write JSON output
    std::ofstream json_file("results.json");
    json_file << "{\n";
    json_file << "  \"total_snaps\": " << snaps.size() << ",\n";
    json_file << "  \"joint\": \"shoulder\",\n";
    json_file << "  \"snaps\": [\n";
    for (size_t i = 0; i < snaps.size(); i++) {
        json_file << "    {\"time\": " << snaps[i].time
                  << ", \"acceleration\": " << snaps[i].acceleration << "}";
        if (i < snaps.size() - 1) json_file << ",";
        json_file << "\n";
    }
    json_file << "  ]\n";
    json_file << "}\n";
    json_file.close();
    std::cout << "Results written to results.json" << std::endl;

    // Cleanup
    mj_deleteData(data);
    mj_deleteModel(model);
    return 0;
}