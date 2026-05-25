#include <iostream>
#include <mujoco.h>

int main() {
    // Load the arm model
    char error[1000];
    mjModel* model = mj_loadXML("/Users/aj/Neuro-Motion/mujoco_arm_demo/arm.xml", nullptr, error, 1000);

    if (!model) {
        std::cerr << "Failed to load the model: " << error << std::endl;
        return 1;
    }

    // Simulate the model data
    mjData* data = mj_makeData(model);

    // Run simulation
    mj_step(model, data);

    std::cout << "Model loaded successfully!" << std::endl;
    std::cout << "Number of joints: " << model->njnt << std::endl;
    std::cout << "Number of bodies: " << model->nbody << std::endl;

    // Cleanup Memory
    mj_deleteData(data);
    mj_deleteModel(model);

    return 0;

}