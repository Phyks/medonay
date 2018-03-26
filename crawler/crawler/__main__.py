from datetime import date
from datetime import datetime
from datetime import timedelta
from getpass import getpass
from time import sleep
from imaplib import IMAP4
import email
import json
import os
import sys

from dateutil import parser
from dateutil.tz import tzutc
from imbox import Imbox
from imbox.parser import parse_email
import requests


VALID_CONTENT_TYPES = [ 'text/plain', 'text/html' ]


class MailCrawler(object):
    parser_urls = None
    indexer_url = os.environ['INDEXER_URL']

    def __init__(self):
        self.imap_url = os.environ.get('IMAP_URL')
        self.imap_user = os.environ.get('IMAP_USER')
        self.imap_pass = os.environ.get('IMAP_PASS')

    def get_parsers(self):
        """Retrieves a list of parser hosts"""
        if self.parser_urls is None:
            self.parser_urls = []
            parser_format = 'PARSER_{}'
            parser_index = 1
            parser_url = os.environ.get(parser_format.format(parser_index))
            while parser_url is not None:
                self.parser_urls.append(parser_url)
                parser_index += 1
                parser_url = os.environ.get(parser_format.format(parser_index))

        return self.parser_urls

    def parse_message(self, message):
        """Parses tokens from an email message"""
        text = self.get_email_text(message)
        if not text:
            print('No email text returned')
            return []

        results = []
        for parser_url in self.get_parsers():
            # print('Parsing email text... ', text)
            response = requests.post(
                parser_url+'/parse',
                json={
                    'subject': message.subject,
                    'message': text,
                },
            )
            response.raise_for_status()
            print('Got response', response.text)
            results += response.json()
        return results

    def get_server(self):
        """Returns an active IMAP server"""
        return Imbox(
            self.imap_url,
            username=self.imap_user,
            password=self.imap_pass,
            ssl=True,
        )

    def get_email_text(self, message):
        """Retrieves the text body of an email message"""
        body = message.body.get('plain') or message.body.get('html')
        if not body:
            return None
        # Concat all known body content together since it doesn't really matter
        return ''.join([text for text in body if isinstance(text, str)])

    def index_token(self, message):
        """Sends a token from the parser to the indexer"""
        response = requests.post(
            self.indexer_url+'/token',
            json=message,
        )
        response.raise_for_status()
        return response.json()

    def process_message(self, message):
        """Process a single email message"""
        for result in self.parse_message(message):
            result.update({
                'subject': message.subject,
            })
            print('Parsed result: ', result)
            print('Indexed result: ', self.index_token(result))


    def process_messages(self, server, since_date, last_message=0):
        for uid, message in server.messages(date__gt=since_date):
            uid = int(uid)
            if uid <= last_message:
                print('DDB Already seen message with uid {}. Skipping'.format(uid))
                continue

            print(
                'Processing message uid {} message_id {} '
                'with subject "{}"'.format(
                    uid, message.message_id, message.subject
                )
            )
            self.process_message(message)

            # Update since_date
            message_date = parser.parse(message.date)
            print('DDB Processed message. Message date: {} Old date: {}'.format(
                message_date, since_date
            ))
            since_date = max(since_date, message_date)
            print('DDB Since date is now ', since_date)
            last_message = max(uid, last_message)

        return since_date, last_message


    def run_against_imap(self):
        print('Starting crawler')
        # TODO: Put server into some kind of context manager and property
        with self.get_server() as server:
            # TODO: parameterize startup date, maybe relative
            since_date = datetime.now(tzutc()) - timedelta(days=15)
            last_message = 0
            while True:
                print('Lets process')
                since_date, last_message = self.process_messages(
                    server,
                    since_date,
                    last_message=last_message
                )
                print('DDB Processed all. New since_date', since_date)
                # TODO: parameterize sleep
                # Sleep for 10 min
                sleep(10 * 60)

    def run_against_stdin(self):
        print('Running crawler on stdin')
        message = parse_email(sys.stdin.read())
        self.process_message(message)
        print('Done')

    def run(self):
        if self.imap_url and self.imap_user and self.imap_pass:
            while True:
                try:
                    self.run_against_imap()
                except IMAP4.abort:
                    print('Imap abort. We will try to reconnect')
                    pass
        else:
            self.run_against_stdin()


if __name__ == '__main__':
    MailCrawler().run()