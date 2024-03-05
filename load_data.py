import os
from sklearn.model_selection import train_test_split
import torch.utils.data as data
import numpy as np
import torch
from PIL import Image
from torchvision import transforms, models

class ImageDataset(data.Dataset):
    def __init__(self, root_dir, train=True, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        self.training_file = "train_set.txt"
        self.validation_file = "validation_set.txt"
        self.test_file = "test_set.txt"
        self.train    = train
        self.class_to_idx = {}
        self.image_filenames = []
        self.labels = []
        self.transform = transform

        with open(self.training_file, 'r') as file:
            for line in file:
                parts = line.split(" ")
                self.image_filenames.append(parts[0])
                self.labels.append(parts[1].strip())

        self.class_to_idx = self.convert_label_to_ix(self.labels)
        print(self.class_to_idx)

        print("Done iterating through files")
        print(len(self.labels))

    def __len__(self):
        """
        :return: The total number of samples
        """
        return len(self.labels)

    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            tuple: (image, target) where target is index of the target class.
        """

        img_path  = self.image_filenames[index]
        img = Image.open(img_path).convert('RGB')

        if self.transform is not None:
            img = self.transform(img)
        else:
            img = transforms.ToTensor()(img)

        label = self.class_to_idx[self.labels[index]]

        label = torch.tensor(label, dtype=torch.long)
        sample = {'image': img, 'label': label, 'filepath': self.image_filenames[index]}

        return sample

    def convert_label_to_ix(self, label_list):
        classes = list(set(label_list))
        class_to_idx = {class_name: idx for idx, class_name in enumerate(classes)}
        return class_to_idx


'''
Class that iterates through the directories and creates files for the different datasets.
With the help of the sklearn library data is split into 3 sets (training, validation and test).
The split data is stored in each its own respective file.
In those files, the datapath to each image and the coresponding label is stored.
The stucture is the following:
    data_path_to_image.png label
    data_path_to_image.png label
    data_path_to_image.png label
    data_path_to_image.png label
    ...
Later on, the torch.Datasets will go to these files and fetch the path to the images.
This is done to avoid loading all the images in memory all at once.
'''
class DataSplitter():
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.validation_size = 2000
        self.test_size = 3000
        self.files, self.labels = self.load_files(self.root_dir)
        self.create_dataset(self.files, self.labels)

    def load_files(self, root):
        files = []
        labels = []
        for sub_dir in os.listdir(root):
            sub_dir_path = os.path.join(root, sub_dir)
            if os.path.isdir(sub_dir_path):
                files_in_subdir = [
                    f
                    for f in os.listdir(sub_dir_path)
                    if os.path.isfile(os.path.join(sub_dir_path, f))
                ]
                for file in files_in_subdir:
                    files.append(os.path.join(sub_dir_path, file))
                    labels.append(sub_dir_path.split("/")[-1])
        return files, labels

    def save_file_paths(self, file_paths, labels, file_path):
        with open(file_path, "w") as f:
            for path, label in zip(file_paths, labels):
                f.write(f"{path} {label}\n")

    def create_dataset(self, files, labels):
        X_train_temp, X_remaining, y_train_temp, y_remaining = train_test_split(files, labels, test_size=(self.validation_size + self.test_size), stratify=labels, random_state=42)
        X_validation, X_test, y_validation, y_test = train_test_split(X_remaining, y_remaining, test_size=(self.test_size / (self.validation_size + self.test_size)), stratify=y_remaining, random_state=42)

        self.save_file_paths(X_train_temp, y_train_temp, "train_set.txt")
        self.save_file_paths(X_validation, y_validation, "validation_set.txt")
        self.save_file_paths(X_test, y_test, "test_set.txt")



def train(model, optimizer, criterion, num_epochs, data_loader):
    print("---Training---")
    model.train()
    for epoch in range(num_epochs):
        for batch in data_loader:
            inputs = batch['image']
            labels = batch['label']

            optimizer.zero_grad()

            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
        print(f'Epoch {epoch+1}/{num_epochs}, Loss: {loss.item()}')



if __name__ == "__main__":
    root_path = "Images/mandatory1_data/"
    #dataset = DataSplitter(root_path)
    #print("Done creating train, validation and test sets...")
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    dataset = ImageDataset(root_path, transform = transform)
    train_loader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=False, num_workers=1)


    model = models.resnet18(pretrained=True)
    num_classes = len(dataset.class_to_idx)
    model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
    
    model = model.to(device)  # Move the model to GPU or CPU

    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    num_epochs = 10

    train(model, optimizer, criterion, num_epochs, train_loader)