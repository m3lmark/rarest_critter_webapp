# Rarest Critter Web Application

This project is a web application that allows users to search for the rarest critters based on species observations using the iNaturalist API. The application is built using Flask and provides a user-friendly interface to display the results.

## Project Structure

```
rarest_critter_webapp
├── app
│   ├── __init__.py         # Initializes the Flask application
│   ├── routes.py           # Defines the application routes
│   ├── static              # Contains static files (CSS, JS, images)
│   └── templates
│       └── index.html      # HTML template for the main page
├── requirements.txt         # Lists project dependencies
├── run.py                   # Entry point to run the application
└── README.md                # Documentation for the project
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd rarest_critter_webapp
   ```

2. **Create a virtual environment:**
   ```
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. **Install the required dependencies:**
   ```
   pip install -r requirements.txt
   ```

## Usage

1. **Run the application:**
   ```
   python run.py
   ```

2. **Access the application:**
   Open your web browser and go to `http://127.0.0.1:5000`.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.