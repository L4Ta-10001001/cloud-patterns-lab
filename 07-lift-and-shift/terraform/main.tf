# EC2 nueva y red independiente: no modifica el Terraform ni el estado de Lab04/05.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_vpc" "lab07" {
  cidr_block           = "10.70.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "cloudlab-erik-lab07-vpc" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.lab07.id
  cidr_block              = "10.70.1.0/24"
  availability_zone       = null
  map_public_ip_on_launch = true
  tags                    = { Name = "cloudlab-erik-lab07-public" }
}

resource "aws_internet_gateway" "public" {
  vpc_id = aws_vpc.lab07.id
  tags   = { Name = "cloudlab-erik-lab07-igw" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.lab07.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.public.id
  }
  tags = { Name = "cloudlab-erik-lab07-routes" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "ec2" {
  name_prefix = "cloudlab-erik-lab07-"
  description = "SSH and demo HTTP only from student IP"
  vpc_id      = aws_vpc.lab07.id

  ingress {
    description = "SSH desde IP autorizada"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  ingress {
    description = "HTTP demo 8080 desde IP autorizada"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [try(var.http_allowed_cidr, var.allowed_cidr)]
  }

  egress {
    description = "Salida para actualizaciones y resolucion DNS"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "cloudlab-erik-lab07-sg" }
}

resource "aws_key_pair" "migration" {
  count      = var.create_key_pair ? 1 : 0
  key_name   = "cloudlab-erik-lab07-key"
  public_key = file(pathexpand(var.public_key_path))
}

resource "aws_instance" "migration" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  associate_public_ip_address = true
  key_name                    = var.create_key_pair ? aws_key_pair.migration[0].key_name : var.existing_key_name

  metadata_options {
    http_tokens = "required"
  }

  root_block_device {
    volume_size = 10
    volume_type = "gp3"
    encrypted   = true
  }

  depends_on = [aws_route_table_association.public]
  tags       = { Name = "cloudlab-erik-liftshift-ec2" }
}
