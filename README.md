# Запуск проекта на Windows (WSL 2 + Ubuntu)

Руководство для запуска проекта TestDesk API на Windows используя WS2 + Ubuntu.

## Установка WSL2

1. **Установите WSL 2:**
   ```bash
   wsl --install
2. **Перезагрузите ПК. Вы можете установить для WSL другой дистрибутив Linux. Выведите список доступных дистрибутивов:**
    ```bash
   wsl --list --online

3. **Укажите имя дистрибутива Linux, который установить в WSL. Например:**
   ```bash
   wsl --install Ununtu
4. **Установите Ubuntu в WSL:**
   ```bash
   wsl --install Ubuntu

## Установка Docker и Docker-Compose в WSL 2 Ubuntu

- **Обновляем список пакетов:**:
    ```bash
   sudo apt update
- **Затем установите несколько обязательных пакетов, которые позволяют apt использовать пакеты по HTTPS:**
    ```bash
   sudo apt install apt-transport-https ca-certificates curl software-properties-common
- **Добавляем ключ GPG официального репозитория Docker в вашу систему:**
    ```bash
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
- **Добавляем репозиторий Docker:**
    ```bash
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
- **Обновляем список пакетов:**
    ```bash
   sudo apt update
- **Теперь надо убедится, что все нормально и установка будет из репозитория Docker, а не Ubuntu:**
    ```bash
   apt-cache policy docker-ce
   
- **На выходе видим плюс минус такую картину:**
    ```bash
     docker-ce:
       Installed: (none)
       Candidate: 5:20.10.14~3-0~ubuntu-jammy
       Version table:
          5:20.10.14~3-0~ubuntu-jammy 500
            500 https://download.docker.com/linux/ubuntu jammy/stable amd64 Packages
          5:20.10.13~3-0~ubuntu-jammy 500
            500 https://download.docker.com/linux/ubuntu jammy/stable amd64 Packages

- **Ну и финальный штрих, установим Docker:**
    ```bash
   sudo apt install docker-ce
 - **Проверяем работает ли Docker:**
   ```bash
   sudo systemctl status docker
- **На выходе:**
    ```bash
  ● docker.service - Docker Application Container Engine
     Loaded: loaded (/lib/systemd/system/docker.service; enabled; vendor preset: enabled)
     Active: active (running) since Fri 2022-04-01 21:30:25 UTC; 22s ago
    TriggeredBy: ● docker.socket
       Docs: https://docs.docker.com
   Main PID: 7854 (dockerd)
      Tasks: 7
     Memory: 38.3M
        CPU: 340ms
     CGroup: /system.slice/docker.service
             └─7854 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock

- **Разрешаем не root пользователю запускать Docker:**
   ```bash
  sudo usermod -aG docker ${USER}

- **Устанавливаем Docker-compose:**
    ```bash
    mkdir -p ~/.docker/cli-plugins/
    curl -SL https://github.com/docker/compose/releases/download/v2.14.2/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
- **Делаем файл запускаемым:**
    ```bash
    chmod +x ~/.docker/cli-plugins/docker-compose
- **Проверяем, как все работает:**
    ```bash
   docker compose version
- **Увидим плюс минус:**
  ```bash
   Docker Compose version v2.14.2
- **Для удобной работы с docker compose установим пакет make:**
    ```bash
    sudo apt install make

##  Git

- **Конфигурирование:**
    ```bash
    git config --global user.name "ваше имя"
    git config --global user.email email@example.com
- **Создаем SSH-ключи и добавляем в Github:**
    ```bash
    ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
    # Скопируйте содержимое публичного ключа и добавьте его в настройках SSH на GitHub
    cat /root/.ssh/id_rsa.pub

## Сборка и запуск проекта

- **Клонируем себе проект и переходим в папку:**
  ```bash
  git clone git@github.com:deymonster/poll.git
  cd poll
- **Переименуйте env.tmpl в .env::**
  ```bash
  mv env.tmpl .env
- **Используйте команды в Makefile для Ubuntu:**

  - Измените команды в файле Makefile следующим образом: 
     - docker-compose -f docker-compose.yaml build на
     - docker compose -f docker compose.yaml build

- **Сборка проекта:**
    ```bash
    make build
- **Запуск проекта с логами:**
    ```bash
    make run log

***
Swagger будет доступен по адресу:
[http://localhost:5000/docs]((URL))

При старте создаются два контейнера:

 - poll-db (база данных)
 - poll-app (приложение)

После старта вам будет доступен пользователь с максимальными правами:

 - LOGIN -  admin@email.com
 - PASSWORD  -  1Q2w3e4r


Все вопросы пишем сюда -> [https://t.me/Deymonster](URL)


