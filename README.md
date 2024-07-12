# Winter-Dragon-Bot

## Description

Winter-Dragon-Bot is a versatile Discord bot designed to enhance server management, provide entertainment, and offer a wide range of utilities. Developed with Python 3.11 ( and transitioning to 3.12) and leveraging the power of SQLite for data management, this bot is a project that helps with continuous learning and improvement in software development.

## Features

- **Comprehensive Slash Commands**: Offers a broad spectrum of slash commands for various functionalities, enhancing user interaction and server management.
- **Advanced Configuration**: Customizable settings through a config file, allowing for tailored bot behavior to fit specific server needs.
- **Dynamic Logging**: Separate and dynamic log files for different aspects of the bot's operation (Discord, SQL, etc.), including automatic log rotation to conserve disk space.
- **Error Handling**: Extensive error handling mechanisms to ensure stability and reliability.
- **SQLite Integration**: Utilizes SQLite for data storage, management and speed.
- **Docker Support**: Designed to run in Docker containers for easy deployment and scalability. Includes a Python 3.12 container and a SQLite container.

## Installation

### Prerequisites

- Docker and Docker Compose installed on your system.
- Basic knowledge of Docker and containerization.

### Steps

1. **Clone the Repository**: Clone this repository to your local machine using `git clone`.
2. **Docker Setup**: Navigate to the project directory and run `docker-compose build` to build the containers. Then, use `docker-compose up` to start the bot.
3. **Initial Configuration**: On the first run, the bot will require some configuration adjustments marked with `!!` in the `config.ini` file. Follow the instructions to set up the necessary configurations.
4. **Running the Bot**: After configuration, restart the bot using Docker Compose. The bot should now be up and running.

### Note

While it's possible to run the bot directly using `python main.py`, it's recommended to use Docker for a more streamlined and consistent environment.

## Contributing

Contributions to Winter-Dragon-Bot are always welcome, whether it be improvements to the codebase, bug reports, or new features. Please feel free to fork the repository and submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Work In Progress

Some parts of the bot might be a work in progress.

The bot itself has a dedicated extension directory for those extensions.
Extensions inside this directory are not or not fully tested.

There's also the website that needs to be worked on.
This should contain pages to manage bot settings more easily and might have **all** users be able to log in.
The website doesn't have any finalized decisions, and is currently in alpha stage. Anything can and will change.
