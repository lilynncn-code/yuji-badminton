const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')

function replaceInFile(relativePath, replacements) {
	const filePath = path.join(root, relativePath)
	if (!fs.existsSync(filePath)) {
		return
	}

	let content = fs.readFileSync(filePath, 'utf8')
	let changed = false

	for (const [from, to] of replacements) {
		if (content.includes(from)) {
			content = content.replace(from, to)
			changed = true
		}
	}

	if (changed) {
		fs.writeFileSync(filePath, content)
	}
}

replaceInFile('node_modules/@dcloudio/vite-plugin-uni/dist/cli/utils.js', [
	[
`    if (process.env.NODE_ENV === 'development') {
        console.log(uni_cli_shared_1.M['dev.performance'] +
            (process.env.UNI_PLATFORM.startsWith('mp-')
                ? uni_cli_shared_1.M['dev.performance.mp']
                : '') +
            (process.env.UNI_PLATFORM === 'web' || process.env.UNI_PLATFORM === 'h5'
                ? uni_cli_shared_1.M['dev.performance.web']
                : ''));
    }
`,
`    if (process.env.NODE_ENV === 'development' && process.env.UNI_SHOW_DEV_TIPS === 'true') {
        console.log(uni_cli_shared_1.M['dev.performance'] +
            (process.env.UNI_PLATFORM.startsWith('mp-')
                ? uni_cli_shared_1.M['dev.performance.mp']
                : '') +
            (process.env.UNI_PLATFORM === 'web' || process.env.UNI_PLATFORM === 'h5'
                ? uni_cli_shared_1.M['dev.performance.web']
                : ''));
    }
`
	]
])

replaceInFile('node_modules/@dcloudio/uni-cli-shared/dist/checkUpdate.js', [
	[
`async function checkUpdate1(options) { if (process.env.CI)
    return void debugCheckUpdate("isInCI"); if ((0, hbx_1.isInHBuilderX)())
    return void debugCheckUpdate("isInHBuilderX");`,
`async function checkUpdate1(options) { if (process.env.CI || process.env.UNI_CHECK_UPDATE !== 'true')
    return void debugCheckUpdate("skipCheckUpdate"); if ((0, hbx_1.isInHBuilderX)())
    return void debugCheckUpdate("isInHBuilderX");`
	],
	[
`async function checkUpdate1(options) { if (process.env.CI || process.env.UNI_CHECK_UPDATE === 'false')
    return void debugCheckUpdate("skipCheckUpdate"); if ((0, hbx_1.isInHBuilderX)())
    return void debugCheckUpdate("isInHBuilderX");`,
`async function checkUpdate1(options) { if (process.env.CI || process.env.UNI_CHECK_UPDATE !== 'true')
    return void debugCheckUpdate("skipCheckUpdate"); if ((0, hbx_1.isInHBuilderX)())
    return void debugCheckUpdate("isInHBuilderX");`
	]
])

replaceInFile('node_modules/@dcloudio/uni-cloud/lib/uni.plugin.js', [
	[
`            if (process.env.UNI_PLATFORM === 'h5' && !process.env.UNI_SSR_CLIENT) {
                console.log();
                console.log('欢迎将web站点部署到uniCloud前端网页托管平台，高速、免费、安全、省心，详见：https://uniapp.dcloud.io/uniCloud/hosting');
            }
`,
`            if (process.env.UNI_PLATFORM === 'h5' && !process.env.UNI_SSR_CLIENT && process.env.UNI_SHOW_UNICLOUD_TIPS === 'true') {
                console.log();
                console.log('欢迎将web站点部署到uniCloud前端网页托管平台，高速、免费、安全、省心，详见：https://uniapp.dcloud.io/uniCloud/hosting');
            }
`
	]
])

replaceInFile('node_modules/@dcloudio/uni-h5/dist/uni-h5.es.js', [
	[
`          if (status === "error") {
            console.error(result);
          } else if (status === "no_data") {`,
`          if (status === "error") {
            if (process.env.UNI_SHOW_MAP_TIPS === "true") {
              console.error(result);
            }
          } else if (status === "no_data") {`
	]
])
