# Part Select Chatbot 
Mini GraphRAG project for an interview at Instalily. 

## Introduction
This project is a comprehensive application that combines a backend powered by FastAPI and a Neo4j graph database and a frontend developed with React.js. The application leverages GenAI, specifically OpenAI's models, to perform intelligent graph querying and similarity searches on a dataset of products, parts, and associated information.

## Project Structure
The project is organized as follows:
```
.
├── Makefile                # Makefile to manage project commands
├── README.md               # Project documentation
├── backend                 # Backend folder containing the core logic and APIs
│   ├── __init__.py
│   ├── core                # Core functionalities and utilities
│   ├── environment.yml     # Conda environment configuration
│   ├── graph_rag           # Graph-based retrieval-augmented generation modules
│   ├── main.py             # Main entry point for the backend server
│   ├── notebooks           # Jupyter notebooks for experimentation
│   ├── pylint.conf         # Pylint configuration
│   ├── scraper             # Web scraping modules
└── frontend                # Frontend folder containing the web application
```

## Quick Setup
The backend is already running on a [Render](https://render.com) instance at: https://partselect-chatbot.onrender.com. To use all the data I already collected, you just have to build the frontend image and upload it in [Chrome Extension](chrome://extensions/).

1. **Clone the Repository**:
   First, clone the repository to your local machine.
   ```bash
   git clone <repository_url>
   cd <repository_directory>
   ```

2. **Install dependencies**:
   Ensure that you have Node.js and Conda installed. Then, run the following command to install all necessary dependencies:
   ```bash
   make install
   conda activate instalily_env
   ```

3. **Build the frontend**:
   To build the frontend for production, run:
   ```bash
   make build
   ```

4. **Load the frontend in Chrome Extension**

## Full Project Setup
To set up the project, follow these steps:

1. **Clone the Repository**:
   First, clone the repository to your local machine.
   ```bash
   git clone <repository_url>
   cd <repository_directory>
   ```

2. **Create the environment file**:
  Create a `.env` file and add your keys and infos for OpenAI and Neo4J:
    ```.env
    OPENAI_API_KEY=<your-openai-api-key>
    NEO4J_CURRENT_URI=<neo4j-uri>
    NEO4J_CURRENT_USERNAME=<neo4j-username>
    NEO4J_CURRENT_PASSWORD=<neo4j-password>
    ```

3. **Install dependencies**: 
   Ensure that you have Node.js and Conda installed. Then, run the following command to install all necessary dependencies:
   ```bash
   make install
   conda activate instalily_env  
   ```

4. **Collect the data**:
  To collect the data, you have to:
  - scrape models 
    ```bash
    python3 -m backend.scraper.models_scraper
    ```
  - scrape models details
    ```bash
    python3 -m backend.scraper.models_details_scraper --verbose --driver Firefox --no-proxy --collection popular    
    ```
  - scrape parts details
    ```bash  
    python3 -m backend.scraper.parts_details_scraper --verbose --driver Firefox --no-proxy --collection popular
    ```
  - upload them in Neo4J
    ```bash
    python3 -m backend.graph_rag.ingestion --collection popular
    ```
  - create the vector indexes
    ```bash
    python3 -m backend.graph_rag.vector_indexes --collection popular
    ```

5. **Start the frontend**:
   To start the frontend server locally, run:
   ```bash
   make front
   ```

6. **Start the backend**:
   To start the backend server locally, run:
   ```bash
   make back
   ```

7. **Build the frontend**:
   To build the frontend for production, run:
   ```bash
   make build
   ```

## Main Commands

### Running the chatbot locally
```bash
python3 -m backend.graph_rag.ai_agent --message <your-message>
```

### Linting
To lint the project files, you can use:
```bash
make lint
```

### Formatting
To format the backend Python code using Black, run:
```bash
make format
```

## Notes
- Make sure to activate your Conda environment before running backend commands.
- For any issues with the setup, refer to the `environment.yml` file for dependencies.

## Useful Links
* [Commit convention (with emojis)](https://github.com/kazupon/git-commit-message-convention/blob/master/README.md)
