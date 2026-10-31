import io
import wave
import unittest
from pathlib import Path
from unittest.mock import patch
import test_app_flows as flows
from app.models.chat import ChatMessage,ChatSend


class VoiceRetryChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api
    accepted_chat=flows.AppFlows.accepted_chat

    def recording(self,sample=b'\0\0'):
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as output:
            output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000)
            output.writeframes(sample*3200)
        return buffer.getvalue()

    def test_retry_deduplicates_original_bytes_and_does_not_restore_recalled_voice(self):
        chat=self.accepted_chat();path=f'/chat/chats/{chat}';data=self.recording()
        def send(who=1,status=200,recording=data,key='voice-retry-once'):
            return self.api('POST',path+'/messages/voice',who,status,files={'audio':('voice.wav',recording,'audio/wav')},data={'request_key':key})
        original=send()['message']
        self.assertEqual(send()['message']['id'],original['id'])
        self.assertEqual(len(list((Path(self.folder.name)/'private').iterdir())),1)
        self.assertEqual(self.api('GET','/chat/chats',2)['chats'][0]['unread_count'],1)
        send(status=409,recording=self.recording(b'\1\0'))
        self.assertEqual(len(list((Path(self.folder.name)/'private').iterdir())),1)
        # A sender cannot reuse a text/image request number for a recording.
        self.api('POST',path+'/messages',json={'content':'文字发送','request_key':'shared-send-key'})
        send(status=409,key='shared-send-key')
        self.api('DELETE',path+'/history',2)
        send()
        self.assertEqual(self.api('GET',path+'/messages',2)['messages'],[])
        self.api('POST',path+f"/messages/{original['id']}/recall")
        self.assertTrue(send()['message']['recalled_at'])
        self.assertEqual(list((Path(self.folder.name)/'private').iterdir()),[])
        self.api('GET',path+f"/messages/{original['id']}/audio",2,404)
        send(who=2)
        self.assertEqual(len(list((Path(self.folder.name)/'private').iterdir())),1)
        send(status=422,key='invalid!')
        with self.Session() as db:
            self.assertEqual(db.query(ChatMessage).count(),3)
            self.assertEqual(db.query(ChatSend).count(),3)

    def test_failed_save_leaves_no_recording_file_or_message(self):
        chat=self.accepted_chat();data=self.recording()
        # No row or private file may survive a failed database commit.
        from sqlalchemy.orm import Session
        with patch.object(Session,'commit',side_effect=RuntimeError('isolated failure')):
            with self.assertRaises(RuntimeError):
                self.api('POST',f'/chat/chats/{chat}/messages/voice',files={'audio':('voice.wav',data,'audio/wav')},data={'request_key':'failed-voice-save'})
        self.assertEqual(list((Path(self.folder.name)/'private').iterdir()),[])
        with self.Session() as db:
            self.assertEqual(db.query(ChatMessage).count(),0)
            self.assertEqual(db.query(ChatSend).count(),0)
