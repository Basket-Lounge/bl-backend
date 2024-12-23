# Contributing to bl-backend

Thank you for considering contributing to **bl-backend**! Your contributions help make this project better for everyone.

## Code of Conduct
Please read and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). We aim to maintain a welcoming and inclusive environment for all contributors.

## Getting Started
The steps below will guide you through setting up the development environment for **bl-backend** in Linux/macOS. Docker is required to run the PostgreSQL, Redis, and Centrifugo containers. If you are using Windows and successfully set up the development environment, feel free to make a pull request to update this document.
1. **Clone this repository**
  ```bash
  git clone https://github.com/Basket-Lounge/bl-backend.git
  ```
2. **Create and activate a virtual environment**
  ```bash
  python -m venv venv
  source venv/bin/activate
  ```
3. **Install the required packages**
  ```bash
  pip install -r requirements.txt
  ```
4. **Run a PostgreSQL container for the DB. You must set POSTGRES_PASSWORD and the host storage directory**
  ```bash
  docker run -d -p 127.0.0.1:5432:5432 --name some-postgres -e POSTGRES_PASSWORD=[the password of a user 'postgres'] -v [host directory]:/var/lib/postgresql/data postgres:17.0-alpine3.20
  ```
5. **Run a Redis container**
  ```bash
  docker run -d -p 6379:6379 -it redis/redis-stack:latest
  ```
6. **Run a Centrifugo container for WebSocket communication. If you modify the configuration file and run it, refer to the [official documentation](https://centrifugal.dev/docs/getting-started/installation)**
  ```bash
  # Create a config file for Centrifugo.
  docker run --rm -v [directory to save the Centrifugo configuration file]:/centrifugo centrifugo/centrifugo:v5 centrifugo genconfig
  # Run a Centrifugo container. Enter the directory where the Centrifugo configuration file is saved in [directory to save the Centrifugo configuration file].
  docker run --rm --ulimit nofile=262144:262144 -v [directory to save the Centrifugo configuration file]:/centrifugo -p 8000:8000 centrifugo/centrifugo:v5 centrifugo -c config.json
  ```
7. **Create a .env file and set the environment variables. Get the Google OAuth 2.0 client ID and secret from the following link and set them. [Google Cloud Console](https://developers.google.com/identity/sign-in/web/sign-in)**
  ```bash
   touch .env
  ```
  ```env
  DJANGO_SECRET_KEY=<your_secret_key>
  DB_NAME=<your_db_name>
  DB_USER=postgres
  DB_PASSWORD=<the password of a user 'postgres'>
  DB_HOST=127.0.0.1
  DB_PORT=5432

  # Set the Google client ID and secret for social login.
  GOOGLE_CLIENT_ID=<your_google_client_id>
  GOOGLE_CLIENT_SECRET=<your_google_client_secret>

  # Set the frontend URL. (ex. http://localhost:3000)
  FRONTEND_URL=<frontend URL>

  # Set the Redis URL for Celery.
  REDIS_URL=redis://127.0.0.1:6379
  CELERY_BROKER_URL=redis://127.0.0.1:6379/0
  CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

  # Set the Centrifugo API key for WebSocket.
  CENTRIFUGO_API_KEY=<your_centrifugo_api_key>
  ```
8. **Run Django DB migration**
  ```bash
  DEVELOPMENT=True python3 manage.py migrate
  ```
9. **Run the Django server**
  ```bash
  DEVELOPMENT=True python3 manage.py runserver
  ```
10. **Run Celery Beat for scheduling**
  ```bash
  DEVELOPMENT=True celery -A config worker -l info
  ```
11. **Run Celery Worker for each queue in each bash window**
  ```bash
  DEVELOPMENT=True celery -A backend worker --loglevel=info --concurrency=3 -n high-priority-worker1@%h -Q high_priority
  DEVELOPMENT=True celery -A backend worker --loglevel=info --concurrency=1 -n low-priority-worker1@%h -Q low_priority
  DEVELOPMENT=True celery -A backend worker --loglevel=info --concurrency=3 -n today-game-update-worker1@%h -Q today_game_update
  ```

## Contributing
If you would like to contribute to **bl-backend**, please follow the steps below:
1. **Fork this repository**
2. **Create a new branch**
3. **Make your changes**
4. **Commit your changes**
5. **Push your changes to your fork**
6. **Create a pull request**
7. **Wait for the maintainers to review your pull request**
8. **Make changes if necessary**

## Testing
Make sure to create and run the tests before creating a pull request. You can run the tests with the following command:
```bash
python3 manage.py test
```

## Issues
If you find a bug or have a feature request, please create an issue. We will review your issue and respond as soon as possible.

## License
This project is licensed under the 3-Clause BSD License - see the [LICENSE](LICENSE) file for details.