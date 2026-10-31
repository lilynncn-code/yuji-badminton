import { request, absoluteUrl, utcTime, accountKey, upload, handleStatus } from './request'
import { API_BASE_URL, getAuthToken } from './auth'
import { defaultUser, imageLibrary } from '../data/app-data'

const USER_KEY = 'track-user'
const CONTACT_META_KEY = 'track-chat-contact-meta'


function getUser() {
	return uni.getStorageSync(USER_KEY) || defaultUser
}

export function getChatSelfId() {
	return String(getUser().id || 'me')
}

function readContactMeta() {
	const value = uni.getStorageSync(accountKey(CONTACT_META_KEY))
	return value && typeof value === 'object' ? value : {}
}

export function saveChatContactMeta(id, contact = {}) {
	const contactId = String(id || '')
	if (!contactId) return
	const next = {
		...readContactMeta(),
		[contactId]: {
			name: contact.name || contact.nickname || contact.username || `球友 ${contactId}`,
			nameIsDefault: !(contact.name || contact.nickname || contact.username),
			avatar: contact.avatar || imageLibrary[0].url
		}
	}
	uni.setStorageSync(accountKey(CONTACT_META_KEY), next)
}

function getContact(id) {
    return readContactMeta()[String(id)] || { name: `球友 ${id}`, nameIsDefault: true, avatar: defaultUser.avatar }
}
export function getChatReceiverId(contact = {}) {
    const id = Number(contact.user_id || contact.userId || contact.receiver_id || contact.id)
    return Number.isInteger(id) && id > 0 && String(id) !== getChatSelfId() ? id : 0
}

function toLastMessage(message) {
	if (!message) return ''
    if(message.recalled_at)return '一条消息已撤回'
	if (message.message_type === 'voice') return '[语音]'
	return message.message_type === 'image' ? '[图片]' : message.content || ''
}

function toPageMessage(message) {
	if(message.recalled_at)return {id:String(message.id),chatId:String(message.chat_id),senderId:String(message.sender_id),type:'system',text:String(message.sender_id)===getChatSelfId()?'你撤回了一条消息':'对方撤回了一条消息',createdAt:utcTime(message.created_at),recalled:true}
	const isImage = message.message_type === 'image'
	const isVoice = message.message_type === 'voice'
	return {
		id: String(message.id),
		chatId: String(message.chat_id),
		senderId: String(message.sender_id),
		senderName: String(message.sender_id) === getChatSelfId() ? getUser().name : getContact(message.sender_id).name,
		type: isVoice ? 'voice' : (isImage ? 'image' : 'text'),
		text: isVoice ? '点击播放录音' : (isImage ? '' : message.content || ''),
        audioPath: isVoice ? `/chat/chats/${message.chat_id}/messages/${message.id}/audio` : '',
		image: isImage ? absoluteUrl(message.content || '') : '',
		createdAt: utcTime(message.created_at)
	}
}

function toThread(chat, messages = []) {
	const otherId = String(chat.other_user_id || (String(chat.requester_id) === getChatSelfId() ? chat.receiver_id : chat.requester_id))
	saveChatContactMeta(otherId, { name: chat.other_name, avatar: absoluteUrl(chat.other_avatar) || defaultUser.avatar })
    const other = getContact(otherId)
	const pageMessages = messages.map(toPageMessage)
	return {
		id: String(chat.id),
		memberIds: [String(chat.requester_id), String(chat.receiver_id)],
		otherId,
		otherName: other.name,
		otherNameIsDefault: Boolean(other.nameIsDefault),
		otherAvatar: other.avatar,
		lastMessage: toLastMessage(chat.last_message),
        lastMessageIsSystem: !chat.last_message || Boolean(chat.last_message.recalled_at) || chat.last_message.message_type !== 'text',
		updatedAt: utcTime(chat.updated_at || chat.created_at),
        unreadCount: chat.unread_count || 0,
        otherReadId: chat.other_read_id || 0,
		status: chat.status,
		messages: pageMessages
	}
}

function toRequest(chat) {
	const user = getUser()
	const selfId = getChatSelfId()
	const requesterId = String(chat.requester_id)
	const receiverId = String(chat.receiver_id)
	saveChatContactMeta(chat.other_user_id, { name: chat.other_name, avatar: absoluteUrl(chat.other_avatar) || defaultUser.avatar })
    const requester = requesterId === selfId ? { name: user.name, avatar: user.avatar } : getContact(requesterId)
	const receiver = receiverId === selfId ? { name: user.name, avatar: user.avatar } : getContact(receiverId)
	return {
		id: String(chat.id),
		threadId: String(chat.id),
		fromId: requesterId,
		fromName: requester.name,
		fromNameIsDefault: Boolean(requester.nameIsDefault),
		fromAvatar: requester.avatar,
		toId: receiverId,
		toName: receiver.name,
		toNameIsDefault: Boolean(receiver.nameIsDefault),
		toAvatar: receiver.avatar,
		note: chat.note || '想和你聊聊羽毛球。',
        noteIsDefault: !chat.note,
		status: chat.status,
		createdAt: utcTime(chat.created_at),
		respondedAt: utcTime(chat.updated_at || '')
	}
}

function inboxData(data) {
	const chats = data.chats || []
	return {
		threads: chats.filter((chat) => chat.status === 'accepted').map((chat) => toThread(chat)),
		requests: chats.map(toRequest),
        hasMore:Boolean(data.has_more),nextCursor:data.next_cursor||'',revision:data.revision,
        summary:data.summary
	}
}

function loginContext(){return {owner:getChatSelfId(),token:getAuthToken()}}
function checkLogin(c){if(c.owner!==getChatSelfId()||c.token!==getAuthToken())throw new Error('登录账号已变化，请重新打开聊天')}
async function chatRequest(path,options){const c=loginContext();const result=await request(path,options);checkLogin(c);return result}

export async function fetchChatInbox({kind='all',cursor='',limit=30}={}) {
    return inboxData(await chatRequest(`/chat/chats?kind=${encodeURIComponent(kind)}&limit=${limit}${cursor?'&cursor='+encodeURIComponent(cursor):''}`))
}
export async function fetchChatInboxStatus(ids=[]) {
    return inboxData(await chatRequest('/chat/chats/status'+(ids.length?'?'+ids.map(id=>'ids='+encodeURIComponent(id)).join('&'):'')))
}

export async function fetchChatThread(chatId, query = {}) {
	const params = Object.entries(query).map(([key, value]) => `${key}=${encodeURIComponent(value)}`).join('&')
    const data = await chatRequest(`/chat/chats/${encodeURIComponent(chatId)}/messages${params ? '?' + params : ''}`)
	return { ...toThread(data.chat, data.messages || []), hasMore: data.has_more, messageUpdates:(data.message_updates||[]).map(toPageMessage), changeCursor:data.change_cursor||0 }
}

export async function applyChatRequest(contact) {
	const receiverId = getChatReceiverId(contact)
	if (!receiverId) {
		throw new Error('没有找到对方，暂时不能申请聊天')
	}
	saveChatContactMeta(receiverId, contact)
	const data = await chatRequest('/chat/requests', {
		method: 'POST',
		data: { receiver_id: receiverId, note: contact.note || '' }
	})
	return {
		message: data.message,
		chat: toThread(data.chat),
		request: toRequest(data.chat)
	}
}

export async function acceptChatRequestRemote(chatId) {
	const data = await chatRequest(`/chat/requests/${encodeURIComponent(chatId)}/accept`, { method: 'POST' })
	return {
		message: data.message,
		chat: toThread(data.chat),
		request: toRequest(data.chat)
	}
}

export async function rejectChatRequestRemote(chatId) {
	const data = await chatRequest(`/chat/requests/${encodeURIComponent(chatId)}/reject`, { method: 'POST' })
	return {
		message: data.message,
		chat: toThread(data.chat),
		request: toRequest(data.chat)
	}
}

export async function sendChatMessageRemote(chatId, payload = {}) {
    const c=loginContext()
    const text = String(payload.text || '').trim()
    let image=payload.uploadedImage || payload.image || ''
    if(image && !image.startsWith('https://') && !image.startsWith(`/chat/chats/${chatId}/images/`)) {
        image=(await upload(image,`/chat/chats/${chatId}/images`)).url
        checkLogin(c)
        payload.uploadedImage=image
        payload.onUploaded?.()
    }
    if (!text && !image) throw new Error('先输入消息或选一张图')
    checkLogin(c)
    if(payload.isCurrent&&!payload.isCurrent())throw new Error('已离开聊天，内容保留，可返回后继续发送')
    const data = await chatRequest(`/chat/chats/${encodeURIComponent(chatId)}/messages`, { method: 'POST', data: { content: text, image_url: image, request_key: payload.requestKey } })
    return data.messages.map(toPageMessage)
}
export function sendChatVoiceRemote(chatId, filePath, requestKey) {
    return upload(filePath, `/chat/chats/${encodeURIComponent(chatId)}/messages/voice`, 'audio', requestKey ? {request_key:requestKey} : {})
}
export function markChatRead(chatId, lastMessageId) { return request(`/chat/chats/${chatId}/read`, { method: 'POST', data: { last_message_id: Number(lastMessageId || 0) } }) }
export function cancelChatRequest(chatId) { return request(`/chat/requests/${chatId}`, { method: 'DELETE' }) }
export async function recallChatMessage(chatId,messageId){return toPageMessage(await chatRequest(`/chat/chats/${chatId}/messages/${messageId}/recall`,{method:'POST'}))}
export function clearChatHistory(chatId){return request(`/chat/chats/${chatId}/history`,{method:'DELETE'})}
export function removeChatConversation(chatId){return request(`/chat/chats/${chatId}`,{method:'DELETE'})}
export function openChatConversation(chatId){return request(`/chat/chats/${chatId}/visible`,{method:'POST'})}
export function downloadVoice(path) {
    const c=loginContext()
    if(!c.token)return Promise.reject(new Error('请先登录后收听录音'))
    return new Promise((resolve, reject) => uni.downloadFile({ url: API_BASE_URL + path,
        header: { Authorization: `Bearer ${c.token}` },
        success(result) { try{checkLogin(c)}catch(e){reject(e);return}if (result.statusCode === 200) resolve(result.tempFilePath); else reject(result.statusCode===401?handleStatus(401,{}):new Error('这条录音无法播放，请重试')) },
        fail() { reject(new Error('录音读取失败，请检查网络')) }
    }))
}
