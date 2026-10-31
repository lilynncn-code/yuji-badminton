import { API_BASE_URL } from './auth'

import { request as authRequest } from './request'
function request(path, data) { return authRequest(path, { method: 'POST', data }) }

function get(path) {
	return new Promise((resolve, reject) => {
		uni.request({
			url: `${API_BASE_URL}${path}`,
			method: 'GET',
			success(response) {
				if (response.statusCode >= 200 && response.statusCode < 300) {
					resolve(response.data)
					return
				}
				reject(new Error(response.data?.detail || '请求失败'))
			},
			fail() {
				reject(new Error('无法连接后端'))
			}
		})
	})
}

export function fetchNearbyCourts({ latitude, longitude, radius = 5000, keyword = '羽毛球馆', page = 1 }) {
	return request('/integrations/amap/courts', {
		latitude,
		longitude,
		radius,
		keyword, page
	})
}

export function fetchCityCourts({city, keyword='羽毛球馆', page=1}) {
    return request('/integrations/amap/courts/city', {city,keyword,page})
}

export function fetchAmapStatus() {
	return authRequest('/integrations/amap/status')
}

export function fetchTrainingAdvice(payload) {
	return request('/integrations/doubao/training-advice', payload)
}
