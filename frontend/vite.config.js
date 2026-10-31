import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import path from 'path'

function quietConsolePlugin() {
	return {
		name: 'quiet-console',
		enforce: 'post',
		config(config) {
			const uniCss = config.css || {}
			const uniScss = uniCss.preprocessorOptions?.scss || {}

			return {
				css: {
					...uniCss,
					preprocessorOptions: {
						...uniCss.preprocessorOptions,
						scss: {
							...uniScss,
							silenceDeprecations: [
								...(uniScss.silenceDeprecations || []),
								'legacy-js-api'
							]
						}
					}
				},
				resolve: {
					alias: [
						{
							find: /vue-router\/dist\/vue-router\.esm-bundler\.js$/,
							replacement: path.resolve(
								__dirname,
								'node_modules/@dcloudio/uni-h5/node_modules/vue-router/dist/vue-router.mjs'
							)
						}
					]
				}
			}
		}
	}
}

export default defineConfig({
	plugins: [
		uni({
			inputDir: __dirname
		}),
		quietConsolePlugin()
	]
})
