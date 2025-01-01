import json

from channels.generic.websocket import WebsocketConsumer


class PresenceConsumer(WebsocketConsumer):

    connections = []

    def connect(self):
        self.accept()
        #self.user = self.scope["user"]
        self.connections.append(self)
        self.update_indicator()
        #self.send({'data': "hello my people"})


    def disconnect(self, code):
        self.update_indicator()
        self.connections.remove(self)
        return super().disconnect(code)

    def update_indicator(self, msg):
        for connection in self.connections:
            connection.send(
                text_data=json.dumps(
                    {
                        "msg": "hello",
                        "online": f"{len(self.connections)}",
                    }
                )
            )
