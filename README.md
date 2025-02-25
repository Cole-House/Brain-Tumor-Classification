# Brain Tumor Classification with Streamlit!

## Why?: Scenario and Use-case

These models can assist medical professionals by quickly and accurately detecting, localizing, and classifying brain tumors, reducing diagnostic errors and speeding up treatment planning. They also help in resource-constrained settings by providing scalable, lightweight solutions that enhance diagnostic precision and support early intervention.

## What?: Project Overview

This repository contains a Streamlit-based web application designed for classifying brain MRI scans. Users can upload MRI images, choose which model they want to use for classification, display the model's "thinking" and prediction with various data visualizations, along with proviing a "simple" or "expert" explantion. What I accomplished:

- **Data Processing**: Curated and split datasets (training, validation, and testing) from Kaggle, implementing advanced augmentation techniques to enhance the model’s generalization capabilities.
- **Model Training & Integration**: • Transfer Learning-Based Model: used Xception as base model, adding custom dense and softmax layers for brain-tumor specific predictions (36 convolutional layers and 21 million parameters)
• Custom Convolutional Neural Network (CNN): designed a smaller model for efficiency, combining convolutional layers with max-pooling to extract most important pixels (4 convolutional layers and 4.7 million parameters)
• Utilized Adamax optimizer for dynamic learning rate adjustment.
• Leveraged metrics such as accuracy, precision, recall, F1-score, and confusion matrices for comprehensive evaluation of models.
- **Web Interface**: Developed an intuitive and lightweight interface using Streamlit for seamless user interaction.

[Demo of App](https://www.youtube.com/watch?v=icIuwp4Z8HI)

## How: Quick Start Guide

To set up and run the application locally, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Cole-House/Brain-Tumor-Classification.git
   cd Brain-Tumor-Classification

2. **Install Dependencies**: Ensure you have Python installed, then install the required packages:
   pip install -r requirements.txt
4. **Run the Application**:
   streamlit run app.py
5. **Upload and Classify Images:**:
   • Open the local URL provided by Streamlit in your browser.
   • Use the upload button to select an MRI image.
   • View the classification results displayed on the interface.



