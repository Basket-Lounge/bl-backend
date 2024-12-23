# Contributing to bl-backend

My initial intention of this project was a means to merely graduating from school, since I was basically required to come up with a website. Since I was given a choice to create any website, as a huge basketball fan, it was a no-brainer for me to create a website where people with the same passion as mine may come together and share their thoughts and opinions about basketball. However, as I was working on this project, I realized that this project could be something more than just a school project. I realized that this project could be a great opportunity for people to learn and grow as developers. It would be a waste to simply let this go after I graduate, with all the hours and effort I put into this project. Also previously, I was briefly introduced to this repository for beginners where the first-timers in open-source could freely fork, clone, and make pull requests to the repository. With this and several open-source websites in mind, I thought it would be cool to foster an environment where everyone who is interested in basketball and eager to learn about Django, Django REST framework, Celery, and other technologies could come together and contribute to this project.

The current state of the web application is, as everyone knows, a work in progress. It goes without saying that there are tons of areas that badly need improvement, and it is just something that can not be done by a single person. One of the reasons why I decided to make this project open-source is simply my desire to learn from those that may share their knowledge and experience that may help everyone become a better developer. I am sure that everyone has their own unique way of solving problems, and your insights and ideas may be something that people have never though of before and ultimately find them helpful. Contributing to this project is not only about making the project better, but also about making yourself better. I hope that you will find this project a good opportunity to learn and grow as a developer.

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
9. **Populate the DB with the players of the NBA via Django shell**
  ```bash
  DEVELOPMENT=True python3 manage.py shell
  ```
  ```python
  from player.services import register_players_to_database
  # Register the players of the NBA to the DB. It may take a long time, since it fetches the player data from the NBA API.
  register_players_to_database()
  ```
10. **Run the Django server**
  ```bash
  DEVELOPMENT=True python3 manage.py runserver
  ```
11. **Run Celery Beat for scheduling**
  ```bash
  DEVELOPMENT=True celery -A config worker -l info
  ```
12. **Run Celery Worker for each queue in each bash window**
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

## Appreciation
We sincerely appreciate everyone who contributes to **bl-backend** and helps make this project better. By no means is this project possible without your help, and your invaluable contributions will greatly help this project a better experience for everyone.

## License
This project is licensed under the 3-Clause BSD License - see the [LICENSE](LICENSE) file for details.