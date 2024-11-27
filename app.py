import streamlit as st
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
import plotly.graph_objects as go
import cv2
from tensorflow.keras.models import Sequential
# The rest we use to further build and train our model
from tensorflow.keras.layers import Dense, Dropout, Flatten
from tensorflow.keras.optimizers import Adamax
from tensorflow.keras.metrics import Precision, Recall
# use gemini to produce insights
import google.generativeai as genai
import PIL.Image
import os
from dotenv import load_dotenv
load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# define a directory where we can store the saliency maps. folder within the colab environment
output_dir = 'saliency_maps'
os.makedirs(output_dir, exist_ok=True)

# function that prompts multi-modal Gemini LLM for explanation
def generate_explanation(img_path, model_prediction, confidence, type):
  if type == "Expert":
    prompt = f"""You are acting as an expert neurosurgeon's assistant. You are tasked with providing an accurate and concise analysis of a saliency map from a brain tumor MRI scan.
    The saliency map was generated by a deep learning model trained to classify brain tumors as glioma, meningioma, pituitary tumor, or no tumor.

    The saliency map highlights the regions of the image that the machine learning model is focusing on to make its prediction.

    The deep learning model predicted the image to be of class '{model_prediction}' with a confidence of {confidence * 100:.2f}%.

    In your response:
    - Explain in detail which regions of the brain the model is focusing on, based on the saliency map. Refer specifically to the regions highlighted in light cyan.
    - Discuss possible reasons why the model made this prediction, including any pertinent clinical features.
    - Provide additional suggestions on next steps for diagnosis or treatment based on this analysis.
    - Avoid phrases like 'The saliency map highlights the regions the model is focusing on, which are highlighted in light cyan'.
    - Keep your explanation concise but comprehensive.

    Let's think step by step and verify each aspect carefully.
    """
  else:
    prompt = f"""You are an expert neurologist. You are tasked with explaining a saliency map of a brain tumor MRI scan.
    The saliency map was generated by a deep learning model that was trained to classify brain tumors as either
    glioma, meningioma, pituitary, or no tumor.

    The saliency map highlights the regions of the image that the machine learning model is focusing on to make the prediction.

    The deep learning model predicted the image to be of class '{model_prediction}' with a conficdence of {confidence * 100}%.

    In your response:
    - Explain what regions of the brain the model is focusing on, based on the saliency map. Refer to the regions highlighted
    in light blue cyan, those are the regions where the model is focusing on.
    - Explain possible reasons why the model made the prediction it did.
    - Don't mention anthing like 'The saliency map highlights the regions the model is focusing on, which are highlighted in
    light cyan' in your explanation.
    - Avoid using any overly-complicated medical jargon
    - Keep your explanation to 4 sentences max.
    Let's think step by step about this. verify step by step.
    """
  img = PIL.Image.open(img_path)

  # passing in the prompt and saliency map to gemini
  model = genai.GenerativeModel(model_name="gemini-1.5-flash")
  response = model.generate_content([prompt, img])

  return response.text

# defining the saliency map function
def generate_saliency_map(model, img_array, class_index, img_size):
  with tf.GradientTape() as tape:
    img_tensor = tf.convert_to_tensor(img_array)
    tape.watch(img_tensor)
    predictions = model(img_tensor)
    target_class = predictions[:, class_index]

  gradients = tape.gradient(target_class, img_tensor)
  gradients = tf.math.abs(gradients)
  gradients = tf.reduce_max(gradients, axis=-1)
  gradients = gradients.numpy().squeeze()
  # Resize gradients to match original image size
  gradients = cv2.resize(gradients, img_size)
  # Create a circular mask for the brain area
  center = (gradients.shape[0] // 2, gradients.shape[1] // 2)
  radius = min(center[0], center[1] - 10)
  y, x = np.ogrid[:gradients.shape[0], :gradients.shape[1]]
  mask = (x - center[0])**2 + (y- center[1])**2 <= radius**2
  # Apply mask to gradients
  gradients = gradients * mask
  # Normalize only the brain area
  brain_gradients = gradients[mask]
  if brain_gradients.max() > brain_gradients.min():
    brain_gradients = (brain_gradients - brain_gradients.min()) / (brain_gradients.max() - brain_gradients.min())
  gradients[mask] = brain_gradients
  # Apply a higher threshold
  threshold = np.percentile(gradients[mask], 80)
  gradients[gradients < threshold] = 0
  # Apply more aggresive smoothing
  gradients = cv2.GaussianBlur(gradients, (11,11), 0)
  # Create a heatmap overlay with enhanced contrast
  heatmap = cv2.applyColorMap(np.uint8(255 * gradients), cv2.COLORMAP_JET)
  heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
  # Resize heatmap to match original image with increased opacity
  original_img = image.img_to_array(img)
  superimposed_img = heatmap * 0.7 + original_img * 0.3
  superimposed_img = superimposed_img.astype(np.uint8)

  img_path = os.path.join(output_dir, uploaded_file.name)
  with open(img_path, "wb") as f:
    f.write(uploaded_file.getbuffer())
  saliency_map_path = f'saliency_maps/{uploaded_file.name}'
  # Save the saliency map
  cv2.imwrite(saliency_map_path, cv2.cvtColor(superimposed_img, cv2.COLOR_RGB2BGR))

  return superimposed_img
# using code from earlier because we want to recreate the model the same exact way we trained it
def load_xception_model(model_path):
  img_shape=(299,299,3)
  base_model = tf.keras.applications.Xception(include_top=False, weights="imagenet",
                                              input_shape= img_shape, pooling='max')

  model = Sequential([
      base_model,
      Flatten(),
      Dropout(rate= 0.3),
      Dense(128, activation= "relu"),
      Dropout(rate=0.25),
      Dense(4, activation= 'softmax')
  ])
  model.build((None,)+ img_shape)
  model.compile(Adamax(learning_rate= 0.001),
              loss= 'categorical_crossentropy',
              metrics= ['accuracy',
              Precision(),
              Recall()])
  model.load_weights(model_path)
  return model


st.title("Brain Tumor Classification")

st.write("Upload an image of a Brain MRI scan to classify.")
# create upload functionality for users
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
  # let users choose which model to use with radio button
  selected_model = st.radio(
      "Selected Model",
      ("Transfer Learning - Xception", "Custom CNN")
  )

  if selected_model == "Transfer Learning - Xception":
    model = load_xception_model('/content/xception_model.weights.h5')
    img_size = (299, 299)
  else:
    model = load_model('/content/cnn_model.h5')
    img_size = (224, 224)

  labels = ["Glioma", "Meningioma", "No tumor", "Pituitary"]
  # load in target image
  img = image.load_img(uploaded_file, target_size=img_size)
  #  convert the image to an array and then we normalize it.
  #  so the pixel values are between zero and one because this is also how the models were trained
  img_array = image.img_to_array(img)
  img_array = np.expand_dims(img_array, axis=0)
  img_array /= 255.0

  prediction = model.predict(img_array)
  # Get the class with the highest probability
  class_index = np.argmax(prediction[0])
  result = labels[class_index]

  # st.write(f'Predicted Class: {result}')
  # st.write("Predictions:")
  # for label , prob in zip(labels, prediction[0]):
  #   st.write(f"{label}: {prob:.4f}")

  saliency_map = generate_saliency_map(model, img_array, class_index, img_size)
  # add 2 columns in the streamlit UI one with image and one with saliency map
  col1, col2 =st.columns(2)
  with col1:
    st.image(uploaded_file, caption='Uploaded Image', use_container_width=True)
  with col2:
    st.image(saliency_map, caption='Saliency Map', use_container_width=True)

  # Adding some final UI data visualizations
  st.write("## Classification Results")

  result_container = st.container()
  result_container = st.container()
  result_container.markdown(
      f"""
      
        
          
            Prediction
            
              {result}
            
          
          
          
            Confidence
            
              {prediction[0][class_index]:.4%}
            
          
        
      
       """,
      unsafe_allow_html=True
  )
  # Prepare data for Plotly chart
  probabilities = prediction[0]
  sorted_indices = np.argsort(probabilities)[::-1]
  sorted_labels = [labels[i] for i in sorted_indices]
  sorted_probabilities = probabilities[sorted_indices]

  # Create a plotly bar chart
  fig = go.Figure(go.Bar(
      x = sorted_probabilities,
      y = sorted_labels,
      orientation = 'h',
      marker_color=['cyan' if label == result else 'grey' for label in sorted_labels]
  ))

  # Customize the chart layout
  fig.update_layout(
      title='Probabilities for each class',
      xaxis_title='Probability',
      yaxis_title="Class",
      height=400,
      width=600,
      yaxis=dict(autorange="reversed")
  )

  # Add value labels to to the bars
  for i, prob in enumerate(sorted_probabilities):
    fig.add_annotation(
        x=prob,
        y=i,
        text=f'{prob:.4f}',
        showarrow=False,
        xanchor='left',
        xshift=5
    )

  # Display the Plotly chart
  st.plotly_chart(fig)

  saliency_map_path = f'saliency_maps/{uploaded_file.name}'

  st.write("## Explanation")
  explanation_type = st.radio(
    "Select Explanation Type",
    ("Simple", "Expert"),
    index=0  # Default to "Simple"
  )
  explanation = generate_explanation(saliency_map_path, result, prediction[0][class_index], explanation_type)
  st.write(explanation)
