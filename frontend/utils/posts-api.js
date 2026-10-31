import { request, uploadImage, uploadVideo, absoluteUrl, utcTime } from './request'
import { imageLibrary } from '../data/app-data'
import { getAuthToken } from './auth'
import { postRequestSnapshot } from './post-draft'


function splitContent(value = '') {
	const lines = String(value).split('\n')
	const firstLine = lines.shift()?.trim()
	const rest = lines.join('\n').trim()
	return {
		title: firstLine || '我的羽毛球动态',
		content: rest || firstLine || ''
	}
}

function joinContent(payload) {
	const title = (payload.title || '我的羽毛球动态').trim()
	const content = (payload.content || '').trim()
	return [title, content].filter(Boolean).join('\n')
}

export function toPagePost(post) {
	const body = splitContent(post.content)
	const createdAt = new Date(utcTime(post.created_at)).getTime()
	const updatedAt = new Date(utcTime(post.updated_at)).getTime()
	const hasRealEdit = Number.isFinite(createdAt) && Number.isFinite(updatedAt) && updatedAt - createdAt > 1000
	const comments = (post.comments || []).map(toPageComment)
	return {
		id: String(post.id),
        authorId: Number(post.user_id || post.author?.id),
		authorName: post.author?.name || '球友',
		authorNameIsDefault: !post.author?.name,
		authorAvatar: absoluteUrl(post.author?.avatar || imageLibrary[0].url),
		title: body.title,
		titleIsDefault: !String(post.content || '').split('\n')[0].trim(),
		content: body.content,
		images: (post.image_urls || []).map(absoluteUrl),
        videoUrl: absoluteUrl(post.video_url || ''),
		createdAt: utcTime(post.created_at),
		updatedAt: hasRealEdit ? utcTime(post.updated_at) : '',
		likes: Math.max(post.likes_count || 0, 0),
		comments,
        commentsHasMore:Boolean(post.comments_has_more),
		commentsCount: Math.max(post.comments_count ?? comments.length, 0),
		tags: post.author?.level_tag ? [post.author.level_tag] : ['动态'],
		tagsAreDefault: !post.author?.level_tag,
		isMine: Number(post.user_id || post.author?.id) === Number(uni.getStorageSync('track-user')?.id),
		likedByMe: Boolean(post.liked_by_me),
		canEdit: Boolean(post.can_edit)
	}
}

function toPageComment(comment) {
	return {
		id: String(comment.id),
		postId: String(comment.post_id),
        isMine: Number(comment.user_id) === Number(uni.getStorageSync('track-user')?.id),
		authorName: comment.author?.name || '球友',
		authorNameIsDefault: !comment.author?.name,
		authorAvatar: absoluteUrl(comment.author?.avatar || imageLibrary[0].url),
		content: comment.content || '',
        replyToId:comment.reply_to_id ? String(comment.reply_to_id) : '',
        replyTo:comment.reply_to ? {id:String(comment.reply_to.id),authorName:comment.reply_to.author_name,content:comment.reply_to.content} : null,
		createdAt: utcTime(comment.created_at)
	}
}

export async function fetchPosts(cursor = '', mine = false, following = false, keyword = '') {
    const data = await request(`/posts?page_size=20${cursor?'&cursor='+encodeURIComponent(cursor):''}${mine ? '&mine=true' : ''}${following ? '&following=true' : ''}&keyword=${encodeURIComponent(keyword.trim())}`)
    return { items: (data.items || []).map(toPagePost), total: data.total || 0, hasMore:Boolean(data.has_more),nextCursor:data.next_cursor||'',fromBackup: false }
}
export async function fetchPost(id,commentId) { return toPagePost(await request(`/posts/${encodeURIComponent(id)}${commentId?'?comment_id='+encodeURIComponent(commentId):''}`)) }
export async function fetchPostComments(id,beforeId){const data=await request(`/posts/${encodeURIComponent(id)}/comments${beforeId?'?before_id='+encodeURIComponent(beforeId):''}`);return {items:data.items.map(toPageComment),hasMore:data.has_more}}

function postOperation(options={}){
    const token=getAuthToken()
    return ()=>{if(!token||token!==getAuthToken()||(options.isCurrent&&!options.isCurrent()))throw new Error('页面或登录账号已变化，请重新打开动态')}
}
async function prepareMedia(payload,check){
    const snapshot={...payload,images:[...(payload.images||[])]}
    check();snapshot.videoUrl=await uploadVideo(snapshot.videoUrl||'');check()
    snapshot.images=await Promise.all(snapshot.images.map(value=>{check();return uploadImage(value)}));check()
    return snapshot
}
export async function publishPost(payload,options={}) {
    const check=postOperation(options),prepared=await prepareMedia(payload,check)
    // Persist the exact uploaded addresses and retry key before issuing a write.
    if(!options.savePrepared)throw new Error('发布前未能保存草稿，请重新打开后重试')
    const saved=await options.savePrepared(prepared);check()
    if(!/^[A-Za-z0-9_-]{8,64}$/.test(saved?.requestKey||'')||saved.requestSnapshot!==postRequestSnapshot(prepared))throw new Error('发布前的草稿保存不完整，请重试')
	const content=joinContent(prepared),video_url=prepared.videoUrl,image_urls=prepared.images
	const data = await request('/posts', {
		method: 'POST',
		data: {content,video_url,image_urls,request_key:saved.requestKey}
	})
	return toPagePost(data)
}

export async function savePost(id, payload,options={}) {
    const check=postOperation(options),prepared=await prepareMedia(payload,check)
	const data = await request(`/posts/${encodeURIComponent(id)}`, {
		method: 'PUT',
		data: {
			content: joinContent(prepared),
			video_url: prepared.videoUrl,
			image_urls: prepared.images
		}
	})
	return toPagePost(data)
}

export async function setPostLike(id, liked) {
	const data = await request(`/posts/${encodeURIComponent(id)}/like`, {
		method: liked ? 'POST' : 'DELETE'
	})
	return {
		postId: String(data.post_id),
		liked: Boolean(data.liked),
		likes: Math.max(data.likes_count || 0, 0)
	}
}

export async function publishComment(id, content, options={}) {
    const cleanContent = String(content || '').trim()
    if (!cleanContent) throw new Error('留言不能为空')
    return toPageComment(await request(`/posts/${encodeURIComponent(id)}/comments`, { method: 'POST', data: { content: cleanContent,reply_to_id:options.replyToId?Number(options.replyToId):null,request_key:options.requestKey } }))
}
export function deletePost(id) { return request(`/posts/${id}`, { method: 'DELETE' }) }
export function deleteComment(postId, id) { return request(`/posts/${postId}/comments/${id}`, { method: 'DELETE' }) }
