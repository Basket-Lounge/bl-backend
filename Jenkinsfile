pipeline {
    agent { dockerfile true }
    stages {
        stage('Build Docker Image') {
            steps {
                script {
                    // Build the Docker image from the Dockerfile and tag it with a name
                    def imageName = 'basketlounge-backend:latest'
                    docker.build(imageName)
                }
            }
        }
        stage('Test') {
            steps {
                script {
                    // Run commands inside the container
                    docker.image('basketlounge-backend:latest').inside {
                        sh 'python --version'
                    }
                }
            }
        }
    }
}