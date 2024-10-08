import os
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.layers import Layer

# Custom ScaleLayer to ensure predictions are within the image dimensions
class ScaleLayer(Layer):
    def __init__(self, scale_factors, **kwargs):
        super(ScaleLayer, self).__init__(**kwargs)
        self.scale_factors = scale_factors

    def call(self, inputs):
        return inputs * self.scale_factors

    def get_config(self):
        config = super(ScaleLayer, self).get_config()
        config.update({
            'scale_factors': self.scale_factors.tolist()  # Convert numpy array to list for serialization
        })
        return config

# Constants
NUM_OF_TRAINING_IMG = 89

# Function to load image and position data
def load_data(images_path, positions_path, num_examples, prefix):
    images = []
    positions = []
    for i in range(num_examples):
        # Load and convert image to grayscale
        img = Image.open(os.path.join(images_path, f'{prefix}_{i}.png')).convert('L')
        img = np.array(img)
        images.append(img)

        # Load and parse positions from text file
        with open(os.path.join(positions_path, f'results_{i}.txt')) as f:
            pos = []
            for line in f:
                x, y = line.strip().split(',')
                pos.append([int(x), int(y)])
        positions.append(pos)
    
    return np.array(images), np.array(positions)

# Function to save predicted positions to text files
def save_predicted_positions(predictions, output_folder, num_examples):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for i in range(num_examples):
        with open(os.path.join(output_folder, f'predicted_{i}.txt'), 'w') as f:
            for j in range(len(predictions[i]) // 2):
                f.write(f"{int(predictions[i][2*j])},{int(predictions[i][2*j+1])}\n")

# Paths to training data
images_path = 'training/images'
positions_path = 'training/positions'

# Load training data
images, positions = load_data(images_path, positions_path, NUM_OF_TRAINING_IMG, 'training_example')

# Normalize images
images = images / 255.0
images = images[..., np.newaxis]  # Add channel dimension for CNN

# Reshape positions
positions = positions.reshape(NUM_OF_TRAINING_IMG, -1)

# Split data into training and validation sets
train_images = images[:80]
train_positions = positions[:80]
val_images = images[80:]
val_positions = positions[80:]

# Function to build CNN model
def build_cnn(input_shape, num_outputs, image_width=16, image_height=16):
    scale_factors = np.array([image_width, image_height] * (num_outputs // 2))
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=input_shape),
        MaxPooling2D((2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        Flatten(),
        Dense(128, activation='relu'),
        Dense(num_outputs, activation='sigmoid'),
        ScaleLayer(scale_factors)  # Use custom scaling layer to ensure valid predictions
    ])
    return model

# Model parameters
num_lights = 2
input_shape = (16, 16, 1)  # Adjust based on your image size
num_outputs = 2 * num_lights  # For x and y coordinates of each light source

# Build and compile the CNN model
model = build_cnn(input_shape, num_outputs)
model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')

# Display model summary
model.summary()

# Train the model
model.fit(train_images, train_positions, epochs=50, batch_size=10, validation_data=(val_images, val_positions))

# Save the trained model
model.save('light_position_cnn_model.keras')

print("Model training completed and saved.")
