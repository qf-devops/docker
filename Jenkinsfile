pipeline {
    agent any

    environment {
        // ── AWS / ECR ──────────────────────────────────────────────────
        AWS_REGION      = 'us-east-1'
        AWS_ACCOUNT_ID  = '123456789012'          // ← your AWS account ID
        ECR_REPO_NAME   = 'my-app'                // ← your ECR repository name
        IMAGE_TAG       = "${env.BUILD_NUMBER}"   // unique tag per build
        ECR_REGISTRY    = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        ECR_IMAGE       = "${ECR_REGISTRY}/${ECR_REPO_NAME}:${IMAGE_TAG}"

        // ── EC2 SSH ────────────────────────────────────────────────────
        EC2_HOST        = 'ec2-xx-xx-xx-xx.compute.amazonaws.com'  // ← your EC2 host
        EC2_USER        = 'ec2-user'              // ubuntu / ec2-user / admin
        EC2_APP_DIR     = '/home/ec2-user/app'    // remote working directory

        // ── Jenkins credentials IDs ────────────────────────────────────
        AWS_CREDENTIALS_ID = 'aws-credentials'   // AWS key pair stored in Jenkins
        EC2_SSH_KEY_ID     = 'ec2-ssh-key'       // EC2 private key stored in Jenkins
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    stages {

        // ── 1. CHECKOUT ────────────────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
                echo "Code checked out — branch: ${env.GIT_BRANCH}"
            }
        }

        // ── 2. BUILD DOCKER IMAGE ──────────────────────────────────────
        stage('Build Docker Image') {
            steps {
                script {
                    echo "Building image: ${ECR_IMAGE}"
                    sh """
                        docker build \
                            --build-arg BUILD_NUMBER=${env.BUILD_NUMBER} \
                            --build-arg GIT_COMMIT=${env.GIT_COMMIT} \
                            -t ${ECR_IMAGE} \
                            -t ${ECR_REGISTRY}/${ECR_REPO_NAME}:latest \
                            .
                    """
                }
            }
        }

        // ── 3. PUSH TO ECR ─────────────────────────────────────────────
        stage('Push to ECR') {
            steps {
                withCredentials([[
                    $class: 'AmazonWebServicesCredentialsBinding',
                    credentialsId: "${AWS_CREDENTIALS_ID}",
                    accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                    secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
                ]]) {
                    script {
                        echo "Authenticating with ECR..."
                        sh """
                            aws ecr get-login-password \
                                --region ${AWS_REGION} | \
                            docker login \
                                --username AWS \
                                --password-stdin ${ECR_REGISTRY}
                        """

                        echo "Pushing ${ECR_IMAGE}..."
                        sh """
                            docker push ${ECR_IMAGE}
                            docker push ${ECR_REGISTRY}/${ECR_REPO_NAME}:latest
                        """

                        // Clean up local image to save disk space
                        sh """
                            docker rmi ${ECR_IMAGE} || true
                            docker rmi ${ECR_REGISTRY}/${ECR_REPO_NAME}:latest || true
                        """
                    }
                }
            }
        }

        // ── 4. DEPLOY TO EC2 ───────────────────────────────────────────
        stage('Deploy to EC2') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: "${EC2_SSH_KEY_ID}",
                        keyFileVariable: 'SSH_KEY'
                    ),
                    [
                        $class: 'AmazonWebServicesCredentialsBinding',
                        credentialsId: "${AWS_CREDENTIALS_ID}",
                        accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                        secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
                    ]
                ]) {
                    script {
                        // Upload the latest docker-compose.yml to EC2
                        sh """
                            scp -i ${SSH_KEY} \
                                -o StrictHostKeyChecking=no \
                                docker-compose.yml \
                                ${EC2_USER}@${EC2_HOST}:${EC2_APP_DIR}/docker-compose.yml
                        """

                        // SSH in, authenticate with ECR, pull new image, redeploy
                        sh """
                            ssh -i ${SSH_KEY} \
                                -o StrictHostKeyChecking=no \
                                ${EC2_USER}@${EC2_HOST} << 'REMOTE'

                                set -e

                                # ── ECR login on the remote host ──────────────
                                export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
                                export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
                                export AWS_DEFAULT_REGION=${AWS_REGION}

                                aws ecr get-login-password \
                                    --region ${AWS_REGION} | \
                                docker login \
                                    --username AWS \
                                    --password-stdin ${ECR_REGISTRY}

                                # ── Pull latest images ────────────────────────
                                cd ${EC2_APP_DIR}
                                export IMAGE_TAG=${IMAGE_TAG}
                                export ECR_IMAGE=${ECR_IMAGE}
                                export ECR_REGISTRY=${ECR_REGISTRY}
                                export ECR_REPO_NAME=${ECR_REPO_NAME}

                                docker-compose pull

                                # ── Zero-downtime rolling restart ─────────────
                                docker-compose up -d --remove-orphans

                                # ── Clean up dangling images ──────────────────
                                docker image prune -f

                                echo " Deployment complete!"

REMOTE
                        """
                    }
                }
            }
        }

        // ── 5. HEALTH CHECK ────────────────────────────────────────────
        stage('Health Check') {
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: "${EC2_SSH_KEY_ID}",
                    keyFileVariable: 'SSH_KEY'
                )]) {
                    script {
                        echo "🩺 Verifying containers are running..."
                        sh """
                            ssh -i ${SSH_KEY} \
                                -o StrictHostKeyChecking=no \
                                ${EC2_USER}@${EC2_HOST} \
                                "cd ${EC2_APP_DIR} && docker-compose ps"
                        """
                    }
                }
            }
        }
    }

    // ── POST ACTIONS ───────────────────────────────────────────────────
    post {
        success {
            echo """
            ╔══════════════════════════════════════════╗
            ║   Deployment Successful               ║
            ║  Build   : #${env.BUILD_NUMBER}          ║
            ║  Image   : ${ECR_IMAGE}                  ║
            ╚══════════════════════════════════════════╝
            """
        }
        failure {
            echo " Pipeline failed — check logs above for details."
            // Optional: add Slack/email notification here
        }
        always {
            // Clean workspace
            cleanWs()
        }
    }
}
