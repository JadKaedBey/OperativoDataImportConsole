```markdown
# Operativo Import Console

This repository contains a PyQt5 application for uploading data to MongoDB, generating QR codes, and more.

## Table of Contents

- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Building the Application](#building-the-application)
- [Usage](#usage)
- [Environment Variables](#environment-variables)
- [Major Dependencies](#major-dependencies)


## Installation

### Using conda

1. Create a new conda environment and activate it:

    ```sh
    conda create --name data-uploader python=3.8
    conda activate data-uploader
    ```

2. Install the required dependencies:

    ```sh
    conda install pyqt=5 pandas pil pymongo
    pip install qrcode
    ```

### Using pip

1. Create a virtual environment and activate it:

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

2. Install the required dependencies:

    ```sh
    pip install PyQt5 pandas pymongo Pillow qrcode
    ```

## Running the Application

To run the application, use the following command:

```sh
python pyqt_console.py
```

## Building the Application

To build the application into an executable using PyInstaller, follow these steps:

1. Install PyInstaller:

    ```sh
    pip install pyinstaller
    ```

2. Use PyInstaller to create an executable:

    ```sh
    pyinstaller --onefile --windowed main.py
    ```

    This will generate a `dist` directory containing the `pyqt_console.exe` file on Windows or `main` on macOS/Linux.

## Usage

1. **Login**: Enter your MongoDB username and password to connect to the database.
2. **Queue Data**: Upload a CSV file to queue data for uploading.
3. **Clear Queued Data**: Clear the data currently queued.
4. **Upload Queued Data**: Upload the queued data to MongoDB.
5. **Generate QR Codes**: Generate and save QR codes for users and orders.
6. **Upload Orders**: Upload orders from an Excel file.
7. **Export Data**: Export data from MongoDB to a CSV file.

### Screenshots

TODO

## Environment Variables

To ensure that sensitive information, such as MongoDB connection strings, is not pushed to the repository I have setup some environment variables.

The .env file can be found on Operativo's Company Google Drive

## Major Dependencies

Here are the major dependencies used in this project:


- `numpy 1.26.4`
- `numpy-base 1.26.4`
- `openjpeg 2.4.0`
- `openssl 3.0.14`
- `pandas 2.2.1`
- `pefile 2023.2.7`
- `pillow 10.3.0`
- `pip 24.0`
- `ply 3.11`
- `pyinstaller 5.13.2`
- `pyinstaller-hooks-contrib 2022.14`
- `pymongo 4.6.3`
- `pyqt 5.15.10`
- `python-dotenv 1.0.1`
- `qrcode 7.4.2`
- `qt-main 5.15.2`
- `sqlite 3.45.3`
