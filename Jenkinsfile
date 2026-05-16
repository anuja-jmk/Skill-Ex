pipeline {
    agent any

    triggers { 
        githubPush() 
    }

    environment {
        DOCKER_HUB = credentials('DockerHubCred')
        GITHUB_REPO_URL = 'https://github.com/aie007/Skill-Ex.git'
        EMAIL_TO = 'aieshah9241@gmail.com, 203ajmk@gmail.com'
        KUBECONFIG = "/var/lib/jenkins/kube-minikube/config"
        MINIKUBE_HOME = "/var/lib/jenkins/kube-minikube/.minikube"
        // Change Detection Flags
        // INGESTION_CHANGED = 'false'
        // DASHBOARD_CHANGED = 'false'
        // ML_CHANGED = 'false'
        // MLFLOW_CHANGED = 'false'
        // ELK_CHANGED = 'false'
        RAPIDAPI_KEY = credentials('rapidapi-key')
        ANSIBLE_ROLES_PATH = "${WORKSPACE}/ansible/roles"
    }

    options {
        // Stops Jenkins from checking out code before the cleanup step runs
        skipDefaultCheckout(true) 
    }
    
    stages {
        stage('Clean Workspace') {
            steps {
                sh 'git clean -fdx'
                sh 'git reset --hard HEAD'
                // Deletes the workspace directory before the build starts
                cleanWs()
                checkout scm
            }
        }

        stage('Checkout') {
            steps {
                git branch: 'main', url: "${GITHUB_REPO_URL}"
            }
        }

        stage('Generate .env') {
            steps {
                script {
                    echo "Generating .env file from Jenkins credentials..."
                    withCredentials([aws(credentialsId: 'b9b4f570-ae9e-4ba8-890d-216c5d94eca6', accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY')]) {
                        sh '''
                        echo "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}" > microservices/.env
                        echo "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}" >> microservices/.env
                        echo "RAPIDAPI_KEY=${RAPIDAPI_KEY}" >> microservices/.env
                        echo "AWS_RAW_BUCKET=amzn-s3-raw-bucket-skillex" >> microservices/.env
                        echo "AWS_PROCESSED_BUCKET=amzn-s3-processed-bucket-skillex" >> microservices/.env
                        echo "AWS_MODELS_BUCKET=amzn-s3-models-bucket" >> microservices/.env
                        echo "PYTHONUNBUFFERED=1" >> microservices/.env
                        echo "APP_ENV=production" >> microservices/.env
                        '''
                    }
                }
            }
        }

      stage('Detect Changes') {
            steps {
                script {
                    echo "Forcing all builds to run regardless of changes."
                    
                    env.INGESTION_CHANGED = 'true'
                    env.DASHBOARD_CHANGED = 'true'
                    env.ML_CHANGED = 'true'
                    env.MLFLOW_CHANGED = 'true'
                    env.ELK_CHANGED = 'true'
                    
                    // Optional: Print to console to verify
                    echo "Flags set: Ingestion=${env.INGESTION_CHANGED}, Dashboard=${env.DASHBOARD_CHANGED}, ML=${env.ML_CHANGED}"
                }
            }
        }

        stage('Run Unit Tests') {
            parallel {
                stage('Test Dashboard') {
                    when { expression { env.DASHBOARD_CHANGED == 'true' } }
                    steps {
                        script {
                            dir('microservices/dashboard') {
                                sh '''
                                    python3 -m venv venv
                                    . venv/bin/activate
                                    pip install -r ./microservices/dashboard/requirements.txt
                                    pip install pytest pytest-mock
                                    pytest --junitxml=dashboard-results.xml
                                '''
                            }
                        }
                    }
                }
            }
        }

        stage('Build & Push Ingestion') {
            when { expression { env.INGESTION_CHANGED == 'true' } }
            steps {
                script {
                    docker.withRegistry('', 'DockerHubCred') {
                        def img = docker.build("${DOCKER_HUB_USR}/microservices-ingestion", "-f microservices/ingestion/Dockerfile microservices")
                        img.push('latest')
                    }
                }
            }
        }

        stage('Build & Push Dashboard') {
            when { expression { env.DASHBOARD_CHANGED == 'true' } }
            steps {
                script {
                    docker.withRegistry('', 'DockerHubCred') {
                        def img = docker.build("${DOCKER_HUB_USR}/microservices-dashboard", "-f microservices/dashboard/Dockerfile microservices")
                        img.push('latest')
                    }
                }
            }
        }

        stage('Build & Push ML Services') {
            when { expression { env.ML_CHANGED == 'true' } }
            steps {
                script {
                    docker.withRegistry('', 'DockerHubCred') {
                        def mlApi = docker.build("${DOCKER_HUB_USR}/microservices-ml-api", "-f microservices/ml/Dockerfile microservices")
                        mlApi.push('latest')
                        
                        def training = docker.build("${DOCKER_HUB_USR}/microservices-model-training", "-f microservices/model_training/Dockerfile microservices")
                        training.push('latest')
                    }
                }
            }
        }

        stage('Build & Push MLflow') {
            when { expression { env.MLFLOW_CHANGED == 'true' } }
            steps {
                script {
                    docker.withRegistry('', 'DockerHubCred') {
                        def img = docker.build("${DOCKER_HUB_USR}/microservices-mlflow", "microservices/mlflow")
                        img.push('latest')
                    }
                }
            }
        }

        stage('Run Ansible Deployment') {
            steps {
                // script {
                //     withCredentials([aws(credentialsId: 'b9b4f570-ae9e-4ba8-890d-216c5d94eca6', accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY')]) {
                //         ansiblePlaybook(
                //             playbook: 'ansible/deploy.yml',
                //             inventory: 'ansible/inventory.ini',
                //             extraVars: [
                //                 aws_access_key: '${AWS_ACCESS_KEY_ID}',
                //                 aws_secret_key: '${AWS_SECRET_ACCESS_KEY}',
                //                 rapidapi_key:   '${RAPIDAPI_KEY}'
                //             ]
                //         )
                //     }
                // }
                echo 'Triggering Ansible Playbook with Vault Decryption...'
        
                // Pull the vault password securely from Jenkins Credentials
                withCredentials([string(credentialsId: 'ANSIBLE_VAULT_PASSWORD', variable: 'VAULT_PASS')]) {
                    script {
                        // Write the password to a temporary file that Ansible can read
                        sh 'echo "$VAULT_PASS" > .vault_pass'
                        
                        // Run the playbook, passing the vault password file flag
                        sh '''
                            ansible-playbook -i ansible/inventory.ini ansible/deploy.yml \
                            --vault-password-file .vault_pass
                        '''
                        
                        // Clean up the password file immediately so it doesn't linger
                        sh 'rm -f .vault_pass'
                    }
                }
            }
        }
    }

    post {
        success {
            mail to: "${EMAIL_TO},203ajmk@gmail.com",
                 subject: "SUCCESS: Skill-Ex Build '${env.JOB_NAME} [${env.BUILD_NUMBER}]'",
                 body: "Great news! The Skill-Ex microservices were successfully built and deployed.\n\nBuild URL: ${env.BUILD_URL}"
        }
        failure {
            mail to: "${EMAIL_TO},203ajmk@gmail.com",
                 subject: "FAILURE: Skill-Ex Build '${env.JOB_NAME} [${env.BUILD_NUMBER}]'",
                 body: "Attention: The Skill-Ex build failed. Please check the logs immediately.\n\nBuild URL: ${env.BUILD_URL}"
        }
    }
}
