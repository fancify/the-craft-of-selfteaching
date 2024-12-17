terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-1"  # Tokyo region for lower latency to Binance
}

# VPC for the strategy server
resource "aws_vpc" "strategy_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "vegas-strategy-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "strategy_igw" {
  vpc_id = aws_vpc.strategy_vpc.id

  tags = {
    Name = "vegas-strategy-igw"
  }
}

# Public Subnet
resource "aws_subnet" "strategy_subnet" {
  vpc_id                  = aws_vpc.strategy_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-northeast-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "vegas-strategy-subnet"
  }
}

# Route Table
resource "aws_route_table" "strategy_rt" {
  vpc_id = aws_vpc.strategy_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.strategy_igw.id
  }

  tags = {
    Name = "vegas-strategy-rt"
  }
}

# Route Table Association
resource "aws_route_table_association" "strategy_rta" {
  subnet_id      = aws_subnet.strategy_subnet.id
  route_table_id = aws_route_table.strategy_rt.id
}

# Security Group
resource "aws_security_group" "strategy_sg" {
  name        = "vegas-strategy-sg"
  description = "Security group for Vegas Channel strategy server"
  vpc_id      = aws_vpc.strategy_vpc.id

  # Grafana UI
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "vegas-strategy-sg"
  }
}

# EC2 Instance
resource "aws_instance" "strategy_server" {
  ami           = "ami-0d52744d6551d851e"  # Ubuntu 22.04 LTS in Tokyo region
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.strategy_subnet.id

  vpc_security_group_ids = [aws_security_group.strategy_sg.id]
  key_name              = "vegas-strategy-key"

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  user_data = <<-EOF
              #!/bin/bash
              # Install Docker
              apt-get update
              apt-get install -y apt-transport-https ca-certificates curl software-properties-common
              curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
              add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
              apt-get update
              apt-get install -y docker-ce docker-ce-cli containerd.io

              # Install Docker Compose
              curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
              chmod +x /usr/local/bin/docker-compose

              # Create app directory
              mkdir -p /app/vegas-strategy
              cd /app/vegas-strategy

              # Start services
              docker-compose up -d
              EOF

  tags = {
    Name = "vegas-strategy-server"
  }
}

# Elastic IP
resource "aws_eip" "strategy_eip" {
  instance = aws_instance.strategy_server.id
  vpc      = true

  tags = {
    Name = "vegas-strategy-eip"
  }
}

# Output values
output "public_ip" {
  value = aws_eip.strategy_eip.public_ip
}

output "instance_id" {
  value = aws_instance.strategy_server.id
}
