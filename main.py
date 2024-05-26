import logging
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
import requests
import json

logger = logging.getLogger(__name__)
EXTENSION_ICON = 'images/icon.png'


def wrap_text(text, max_w):
    words = text.split()
    lines = []
    current_line = ''
    for word in words:
        if len(current_line + word) <= max_w:
            current_line += ' ' + word
        else:
            lines.append(current_line.strip())
            current_line = word
    lines.append(current_line.strip())
    return '\n'.join(lines)


class Test():
    def InvokeRequest(self):
        api_key = ''
        headers = {
            'content-type': 'application/json',
            'api-key': api_key
        }
        body = {
          "messages": [
            {
              "role": "user",
              "content": "How do I read file in c#?"
            },
            {
              "role": "assistant",
              "content": "To read a file in C#, you can use the StreamReader class. Here is an example code snippet:\n\n```csharp\nusing System;\nusing System.IO;\n\nclass Program\n{\n    static void Main()\n    {\n        // Open the file\n        using (StreamReader reader = new StreamReader(\"file.txt\"))\n        {\n            // Read the contents of the file\n            string contents = reader.ReadToEnd();\n            Console.WriteLine(contents);\n        }\n    }\n}\n```\n\nIn this example, we are opening a file called \"file.txt\" and reading its contents using a StreamReader. The using statement ensures that the StreamReader is properly disposed of after use. The ReadToEnd method reads the entire contents of the file into a string, which is then printed to the console."
            },
            {
              "role": "user",
              "content": "How do I Write \"Hello World\""
            }
          ],
          "temperature": 0.5,
          "top_p": 0.95,
          "frequency_penalty": 0,
          "presence_penalty": 0,
          "max_tokens": 800
        }
        body = json.dumps(body)

        logger.info('Request body: %s', str(body))
        logger.info('Request headers: %s', str(headers))

        response = requests.post(
            'https://piotrschat.openai.azure.com/openai/deployments/ulauncher/chat/completions?api-version=2024-04-01-preview', headers=headers, data=body, timeout=10)
        response = response.json()
        choices = response['choices']


class GPTExtension(Extension):
    """
    Ulauncher extension to generate text using GPT-3
    """

    def __init__(self):
        super(GPTExtension, self).__init__()
        logger.info('GPT-3 extension started')
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    """
    Event listener for KeywordQueryEvent
    """

    def on_event(self, event, extension):
        #endpoint = "https://api.openai.com/v1/chat/completions"

        logger.info('Processing user preferences')
        # Get user preferences
        try:
            endpoint = extension.preferences['api_endpoint']
            api_key = extension.preferences['api_key']
            max_tokens = int(extension.preferences['max_tokens'])
            frequency_penalty = float(
                extension.preferences['frequency_penalty'])
            presence_penalty = float(extension.preferences['presence_penalty'])
            temperature = float(extension.preferences['temperature'])
            top_p = float(extension.preferences['top_p'])
            system_prompt = extension.preferences['system_prompt']
            line_wrap = int(extension.preferences['line_wrap'])
            #model = extension.preferences['model']
        # pylint: disable=broad-except
        except Exception as err:
            logger.error('Failed to parse preferences: %s', str(err))
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Failed to parse preferences: ' +
                                    str(err),
                                    on_enter=CopyToClipboardAction(str(err)))
            ])

        # Get search term
        search_term = event.get_argument()
        logger.info('The search term is: %s', search_term)
        # Display blank prompt if user hasn't typed anything
        if not search_term:
            logger.info('Displaying blank prompt')
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Type in a prompt...',
                                    on_enter=DoNothingAction())
            ])

        # Create POST request
        headers = {
            'content-type': 'application/json',
            'api-key': api_key
        }

        body = {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": search_term
                }
            ],
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "max_tokens": max_tokens
        }
        body = json.dumps(body)

        logger.info('Request body: %s', str(body))
        logger.info('Request headers: %s', str(headers))

        # Send POST request
        try:
            logger.info('Sending request')
            response = requests.post(
                endpoint, headers=headers, data=body, timeout=10)
        # pylint: disable=broad-except
        except Exception as err:
            logger.error('Request failed: %s', str(err))
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Request failed: ' + str(err),
                                    on_enter=CopyToClipboardAction(str(err)))
            ])

        logger.info('Request succeeded')
        logger.info('Response: %s', str(response))

        # Get response
        # Choice schema
        #  { message: Message, finish_reason: string, index: number }
        # Message schema
        #  { role: string, content: string }
        try:
            response = response.json()
            choices = response['choices']
        # pylint: disable=broad-except
        except Exception as err:
            logger.error('Failed to parse response: %s', str(response))
            errMsg = "Unknown error, please check logs for more info"
            try:
                errMsg = response['error']['message']
            except Exception:
                pass

            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Failed to parse response: ' +
                                    errMsg,
                                    on_enter=CopyToClipboardAction(str(errMsg)))
            ])

        items: list[ExtensionResultItem] = []
        try:
            for choice in choices:
                message = choice['message']['content']
                message = wrap_text(message, line_wrap)

                items.append(ExtensionResultItem(icon=EXTENSION_ICON, name="Assistant", description=message,
                                                 on_enter=CopyToClipboardAction(message)))
        # pylint: disable=broad-except
        except Exception as err:
            logger.error('Failed to parse response: %s', str(response))
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Failed to parse response: ' +
                                    str(response),
                                    on_enter=CopyToClipboardAction(str(err)))
            ])

        try:
            item_string = ' | '.join([item.description for item in items])
            logger.info("Results: %s", item_string)
        except Exception as err:
            logger.error('Failed to log results: %s', str(err))
            logger.error('Results: %s', str(items))

        return RenderResultListAction(items)


if __name__ == '__main__':
    GPTExtension().run()
    #Test().InvokeRequest()
