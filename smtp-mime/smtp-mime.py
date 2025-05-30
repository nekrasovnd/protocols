#!/usr/bin/env python3
import os
import sys
import argparse
import mimetypes
import smtplib
import getpass
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

# Определяем допустимые расширения изображений
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

def get_images_from_directory(directory):
    """Получить список всех изображений из указанного каталога"""
    images = []
    for entry in os.scandir(directory):
        if entry.is_file():
            if Path(entry.name).suffix.lower() in IMAGE_EXTENSIONS:
                images.append(entry.path)
    return images

def create_message(sender, recipient, subject, images):
    """Создать MIME-сообщение с изображениями во вложении"""
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    msg.set_content("Enjoy the attached pictures!")

    for image_path in images:
        ctype, encoding = mimetypes.guess_type(image_path)
        if ctype is None or not ctype.startswith('image/'):
            continue
        maintype, subtype = ctype.split('/', 1)
        with open(image_path, 'rb') as f:
            img_data = f.read()
        msg.add_attachment(img_data,
                           maintype=maintype,
                           subtype=subtype,
                           filename=os.path.basename(image_path))
    return msg

def send_email(args, msg):
    """Отправить письмо через SMTP"""
    host, port = (args.server.split(':') + ['25'])[:2]
    port = int(port)

    if args.ssl:
        server = smtplib.SMTP_SSL(host, port)
    else:
        server = smtplib.SMTP(host, port)

    try:
        server.set_debuglevel(1 if args.verbose else 0)
        code, initial_msg = server.ehlo()
        if code != 250:
            raise RuntimeError(f"EHLO failed: {initial_msg}")

        if not args.ssl and server.has_extn('starttls'):
            server.starttls()
            code, starttls_msg = server.ehlo()
            if code != 250:
                raise RuntimeError(f"EHLO after STARTTLS failed: {starttls_msg}")

        if args.auth:
            username = args.sender
            password = getpass.getpass("Enter SMTP password: ")
            server.login(username, password)

        code, response = server.mail(args.sender)
        if code != 250:
            raise RuntimeError(f"MAIL FROM failed: {response}")

        code, response = server.rcpt(args.recipient)
        if code not in (250, 251):
            raise RuntimeError(f"RCPT TO failed: {response}")

        code, response = server.data(msg.as_string())
        if code != 250:
            raise RuntimeError(f"DATA failed: {response}")

        print("Message sent successfully.")
    finally:
        server.quit()

def main():
    parser = argparse.ArgumentParser(description='Send all images in a directory as email attachments.')

    parser.add_argument('-s', '--server', required=True, help='SMTP server address (format: host[:port])')
    parser.add_argument('-t', '--to', dest='recipient', required=True, help='Recipient email address')
    parser.add_argument('-f', '--from', dest='sender', default='', help='Sender email address')
    parser.add_argument('--subject', default='Happy Pictures', help='Email subject (optional)')
    parser.add_argument('--ssl', action='store_true', help='Use SSL (default is no)')
    parser.add_argument('--auth', action='store_true', help='Use authentication (login will be prompted)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose SMTP communication')
    parser.add_argument('-d', '--directory', default=os.getcwd(), help='Directory with images (default is current)')

    args = parser.parse_args()

    # Проверка существования каталога
    if not os.path.isdir(args.directory):
        print(f"Error: directory '{args.directory}' not found.")
        sys.exit(1)

    # Сканируем изображения
    images = get_images_from_directory(args.directory)
    if not images:
        print("No images found in directory.")
        sys.exit(1)

    # Создаём письмо
    msg = create_message(args.sender, args.recipient, args.subject, images)

    # Отправляем письмо
    try:
        send_email(args, msg)
    except smtplib.SMTPAuthenticationError:
        print("Authentication failed. Please check your credentials.")
    except smtplib.SMTPException as e:
        print(f"SMTP error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == '__main__':
    main()