#!/usr/bin/env python3
import imaplib
import email
import argparse
import getpass
import os
from email.header import decode_header, make_header

def decode_header_field(field):
    """Декодирование заголовков письма (например, From или Subject)."""
    if field:
        decoded = make_header(decode_header(field))
        return str(decoded)
    return ""

def print_message_info(msg, size):
    """Вывод информации о письме: кому, от кого, тема, дата, размер."""
    subject = decode_header_field(msg.get("Subject", ""))
    from_ = decode_header_field(msg.get("From", ""))
    to = decode_header_field(msg.get("To", ""))
    date = msg.get("Date", "")

    print(f"From: {from_}")
    print(f"To: {to}")
    print(f"Subject: {subject}")
    print(f"Date: {date}")
    print(f"Size: {size} bytes")

    # Аттачи
    attachments = []
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = part.get_filename()
            if filename:
                decoded_filename = decode_header_field(filename)
                attachments.append((decoded_filename, len(part.get_payload(decode=True) or b"")))
    
    print(f"Attachments: {len(attachments)}")
    for name, sz in attachments:
        print(f"  - {name} ({sz} bytes)")
    print("-" * 40)

def main():
    parser = argparse.ArgumentParser(description="IMAP email information fetcher")
    parser.add_argument("-s", "--server", required=True, help="IMAP server (address[:port])")
    parser.add_argument("--ssl", action="store_true", help="Use SSL (IMAPS, port 993 by default)")
    parser.add_argument("-u", "--user", required=True, help="IMAP username")
    parser.add_argument("-n", nargs="*", type=int, help="Message range: N1 [N2]")

    args = parser.parse_args()

    server_parts = args.server.split(":")
    address = server_parts[0]
    port = int(server_parts[1]) if len(server_parts) > 1 else (993 if args.ssl else 143)

    password = getpass.getpass("Enter IMAP password: ")

    try:
        # Подключение к серверу
        if args.ssl:
            imap = imaplib.IMAP4_SSL(address, port)
        else:
            imap = imaplib.IMAP4(address, port)
            imap.starttls()  # STARTTLS для шифрования, если нужно

        # Логин
        imap.login(args.user, password)

        # Выбор папки
        imap.select("INBOX")

        # Получаем все UID сообщений
        status, data = imap.uid("search", None, "ALL")
        if status != "OK":
            print("Error fetching message UIDs")
            return

        all_uids = data[0].split()
        if not all_uids:
            print("No messages found.")
            return
        
        # Вычисляем диапазон
        if args.n:
            n1 = args.n[0] - 1
            n2 = args.n[1] if len(args.n) > 1 else args.n[0]
            msg_uids = all_uids[::-1][n1:n2]
        else:
            msg_uids = all_uids[::-1]

        print(f"Found {len(msg_uids)} message(s).")

        # Загружаем и выводим информацию о каждом сообщении
        for uid in msg_uids:
            status, msg_data = imap.uid("fetch", uid, "(RFC822.SIZE BODY.PEEK[HEADER])")
            if status != "OK":
                print(f"Error fetching message UID {uid.decode()}")
                continue
            
            size = 0
            raw_header = b""
            for part in msg_data:
                if isinstance(part, tuple):
                    if b"RFC822.SIZE" in part[0]:
                        size = int(part[0].split()[2].strip(b")"))
                    raw_header += part[1]
            msg = email.message_from_bytes(raw_header)
            print_message_info(msg, size)

        # Завершение
        imap.logout()

    except imaplib.IMAP4.error as e:
        print("IMAP error:", e)
    except Exception as e:
        print("Unexpected error:", e)

if __name__ == "__main__":
    main()