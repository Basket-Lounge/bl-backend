pipeline {
    agent any
    triggers {
        pollSCM('H/5 * * * *') // Poll every 5 minutes
    }
    environment {
        DB_HOST='user1-main-db-1'
        DB_PORT=5432
        DB_HOST_REPLICA1='user1-secondary-db-1'
        DB_PORT_REPLICA1=5432
        DB_HOST_REPLICA2='user1-secondary-db1-1'
        DB_PORT_REPLICA2=5432
        GOOGLE_CLIENT_ID='asdfasdfasdfasdf'
        GOOGLE_CLIENT_SECRET='asdfasdf'
        FRONTEND_URL='http://localhost:3000'
        REDIS_URL='redis://127.0.0.1:6379'
        CELERY_BROKER_URL='redis://127.0.0.1:6379/0'
        CELERY_RESULT_BACKEND='redis://127.0.0.1:6379/0'
        CENTRIFUGO_API_KEY='asdfgsdfg'
    }
    stages {
        stage('Build Docker Image') {
            steps {
                script {
                    def imageName = 'basketlounge-backend:latest'
                    docker.build(imageName)
                }
            }
        }
        stage('Test') {
            steps {
                script {
                    withEnv([
                        "DJANGO_SECRET_KEY=${env.DJANGO_SECRET_KEY}",
                        "DB_NAME=${env.DB_NAME}",
                        "DB_USER=${env.DB_USER}",
                        "DB_PASSWORD=${env.DB_PASSWORD}"
                    ]) {
                        docker.image('basketlounge-backend:latest').inside('--network jenkins') {
                            sh 'python3 ./manage.py test users'
                        }
                    }
                }
            }
        }
    }
}
