import os, yaml, uuid, logging, time, importlib
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant import config as conf_util, loader
from urllib.parse import quote,unquote

from .api_config import ApiConfig
from .api_sidebar import ApiSidebar
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

VERSION = '2.1.2'
URL = '/ha_sidebar-api'
ROOT_PATH = '/ha_sidebar-local/' + VERSION
StorageFile = 'ha_sidebar.yaml'

def setup(hass, config):
    # 如果没有配置则不运行
    if DOMAIN not in config or DOMAIN in hass.data:
        return True
    api = ApiConfig(hass.config.path('./.storage/.shaonianzhentan'))
    api.api_sidebar = ApiSidebar(hass)
    hass.data[DOMAIN] = api

    # 注册静态目录
    hass.http.register_static_path(ROOT_PATH, hass.config.path("custom_components/" + DOMAIN + "/local"), False)
    api.api_sidebar.add("侧边栏管理", "mdi:view-list-outline", DOMAIN, ROOT_PATH + "/index.html?ver=" + VERSION)

    hass.http.register_view(HassGateView)

    _list = api.read(StorageFile)
    if _list is not None:
        for item in _list:
            wlan_link = item.get('wlan_link', '')
            api.api_sidebar.add(
                item['name'],
                item['icon'],
                item['path'],
                ROOT_PATH + '/link.html?mode=' + str(item['mode']) 
                + '&link=' + quote(item['link'], 'utf-8')
                + '&wlan_link=' + quote(wlan_link, 'utf-8'))

    # 显示插件信息
    _LOGGER.info('''
-------------------------------------------------------------------
    侧边栏管理【作者QQ：635147515】
    
    版本：''' + VERSION + '''    
        
    项目地址：https://github.com/shaonianzhentan/ha_sidebar
-------------------------------------------------------------------''')
    return True

async def async_setup_entry(hass, entry):
    setup(hass, { DOMAIN: entry.data })
    return True

class HassGateView(HomeAssistantView):

    url = URL
    name = DOMAIN
    requires_auth = True
        
    async def post(self, request):
        hass = request.app["hass"]
        try:
            api = hass.data[DOMAIN]
            _list = api.read(StorageFile)
            if _list is None:
                _list = []
            query = await request.json()
            _type = query['type']
            if _type == 'get':
                return self.json({'code':0, 'msg': '查询成功', 'data': _list})
            elif _type == 'add':
                _path = '_' + str(time.time())
                wlan_link = query.get('wlan_link', '')
                mode = str(query['mode'])                
                if mode != '5':
                    # 添加所有菜单
                    api.api_sidebar.add(query['name'], query['icon'], _path, ROOT_PATH 
                    + '/link.html?mode=' + mode 
                    + '&link=' + quote(query['link'],'utf-8')
                    + '&wlan_link=' + quote(wlan_link, 'utf-8'))
                # 添加数据
                _list.append({
                    'name': query['name'],
                    'icon': query['icon'],
                    'link': query['link'],
                    'wlan_link': wlan_link,
                    'mode': mode,
                    'path': _path,
                })
                api.write(StorageFile, _list)
                return self.json({'code':0, 'msg': '保存成功'})
            elif _type == 'delete':
                _path = query['path']
                api.api_sidebar.remove(_path)
                for i in range(len(_list)):
                    if _list[i]['path'] == _path:
                        # 删除数据，保存文件
                        del _list[i]
                        api.write(StorageFile, _list)
                        return self.json({'code':0, 'msg': '删除成功'})
                return self.json({'code':0, 'msg': '数据不存在'})
            elif _type == 'edit':
                _path = query['path']
                wlan_link = query.get('wlan_link', '')
                mode = str(query['mode'])
                if mode == '5':
                    api.api_sidebar.remove(_path)

                for i in range(len(_list)):
                    if _list[i]['path'] == _path:
                        _list[i]['name'] = query['name']
                        _list[i]['icon'] = query['icon']
                        _list[i]['link'] = query['link']
                        _list[i]['wlan_link'] = wlan_link
                        _list[i]['mode'] = mode
                        if mode != '5':
                            api.api_sidebar.add(query['name'],query['icon'],_path,ROOT_PATH 
                            + '/link.html?mode=' + mode 
                            +'&link=' + quote(query['link'], 'utf-8')
                            + '&wlan_link=' + quote(wlan_link, 'utf-8'))

                api.write(StorageFile, _list)
                return self.json({'code':0, 'msg': '保存成功'})
        except Exception as e:
            _LOGGER.error(e)
            return self.json({'code':1, 'msg': '出现异常'})
