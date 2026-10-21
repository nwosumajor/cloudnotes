# CloudNotes VPC Network Architecture (`cloudnotes-vpc`)

## Overview
CloudNotes runs inside a custom AWS Virtual Private Cloud (`cloudnotes-vpc` - `10.0.0.0/16`) designed to isolate public-facing application components from private backend resources.

## Architecture Diagram

```text
                       [ The Internet ]
                              |
                              | (Port 22 / Port 5000 from My IP)
                              v
                 +-------------------------+
                 | Internet Gateway (IGW)  |
                 +-------------------------+
                              |
==============================|==================================
VPC: cloudnotes-vpc (10.0.0.0/16)
                              |
              +---------------+---------------+
              | Public Route Table            |
              | 10.0.0.0/16 -> local          |
              | 0.0.0.0/0   -> igw-xxxxxxxx   |
              +---------------+---------------+
                              |
                              v
     +-------------------------------------------------+
     | Public Subnet (10.0.0.0/20)                     |
     |                                                 |
     |   +-----------------------------------------+   |
     |   | Security Group: cloudnotes-sg           |   |
     |   |  - Inbound: TCP 22 (SSH) from My IP     |   |
     |   |  - Inbound: TCP 5000 (App) from My IP   |   |
     |   |                                         |   |
     |   |   +---------------------------------+   |   |
     |   |   | EC2: cloudnotes-server          |   |   |
     |   |   | (Flask API + SQLite + ElasticIP)|   |   |
     |   |   +---------------------------------+   |   |
     |   +-----------------------------------------+   |
     +-------------------------------------------------+

     +-------------------------------------------------+
     | Private Subnet (10.0.128.0/20)                  |
     | Route Table: 10.0.0.0/16 -> local ONLY          |
     | (No direct route to Internet Gateway)           |
     |                                                 |
     | [ Reserved for future RDS Database / Internal ] |
     +-------------------------------------------------+
=================================================================
Subnet Breakdown
Public Subnet (cloudnotes-subnet-public):

Why it is public: Associated with a Public Route Table that contains a default route (0.0.0.0/0) pointing directly to the Internet Gateway (IGW).

What lives here: The cloudnotes-server EC2 instance (protected by cloudnotes-sg and reachable via an Elastic IP).

Private Subnet (cloudnotes-subnet-private):

Why it is private: Associated with a Private Route Table that only routes internal VPC traffic (10.0.0.0/16 -> local). It has no direct route to the Internet Gateway, preventing any external inbound connections.

Gateway notes: If private instances need outbound internet access in the future (e.g., for OS patches) without being exposed inbound, a NAT Gateway would be placed in the Public Subnet, and the Private Route Table would route 0.0.0.0/0 to that NAT Gateway.