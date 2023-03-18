import importlib
import json
import sys
from multiprocessing import Pipe, Process, freeze_support
import time
import PySimpleGUI as sg
import os
from ruamel.yaml import YAML
from arknights_mower.utils.log import logger
from arknights_mower.data import agent_list
from arknights_mower.__main__ import main

yaml = YAML()
confUrl = './conf.yml';
conf = {}
plan = {}
global window
buffer = ''
line = 0
half_line_index = 0


# 读取写入配置文件
def load_conf():
    global conf
    global confUrl
    if not os.path.isfile(confUrl):
        open(confUrl, 'w')  # 创建空配置文件
    else:
        with open(confUrl, 'r', encoding='utf8') as c:
            conf = yaml.load(c)
            if conf is None:
                conf = {}
    conf['package_type'] = conf['package_type'] if 'package_type' in conf.keys() else 1
    conf['adb'] = conf['adb'] if 'adb' in conf.keys() else ''
    conf['planFile'] = conf['planFile'] if 'planFile' in conf.keys() else './plan.json'  # 默认排班表地址
    conf['free_blacklist'] = conf['free_blacklist'] if 'free_blacklist' in conf.keys() else ''
    conf['ling_xi'] = conf['ling_xi'] if 'ling_xi' in conf.keys() else 1
    conf['rest_in_full'] = conf['rest_in_full'] if 'rest_in_full' in conf.keys() else ''
    conf['mail_enable'] = conf['mail_enable'] if 'mail_enable' in conf.keys() else 0
    conf['account'] = conf['account'] if 'account' in conf.keys() else ''
    conf['pass_code'] = conf['pass_code'] if 'pass_code' in conf.keys() else ''
    conf['maa_enable'] = conf['maa_enable'] if 'maa_enable' in conf.keys() else ''
    conf['maa_path'] = conf['maa_path'] if 'maa_path' in conf.keys() else ''
    conf['maa_adb_path'] = conf['maa_adb_path'] if 'maa_adb_path' in conf.keys() else ''
    conf['maa_weekly_plan'] = conf['maa_weekly_plan'] if 'maa_weekly_plan' in conf.keys() else [
        {"weekday": "周一", "stage": ['AP-5'], "medicine": 0},
        {"weekday": "周二", "stage": ['CE-6'], "medicine": 0},
        {"weekday": "周三", "stage": ['1-7'], "medicine": 0},
        {"weekday": "周四", "stage": ['AP-5'], "medicine": 0},
        {"weekday": "周五", "stage": ['1-7'], "medicine": 0},
        {"weekday": "周六", "stage": ['AP-5'], "medicine": 0},
        {"weekday": "周日", "stage": ['AP-5'], "medicine": 0}
    ]


def write_conf():
    global conf
    global confUrl
    with open(confUrl, 'w', encoding='utf8') as c:
        yaml.default_flow_style = False
        yaml.dump(conf, c)


# 读取排班表
def load_plan(url):
    global plan
    if not os.path.isfile(url):
        with open(url, 'w') as f:
            json.dump(plan, f)  # 创建空json文件
        return
    try:
        with open(url, 'r', encoding='utf8') as fp:
            plan = json.loads(fp.read())
        conf['planFile'] = url
        for i in range(1, 4):
            for j in range(1, 4):
                window[f'btn_room_{str(i)}_{str(j)}'].update('待建造', button_color=('white', '#4f4945'))
        for key in plan:
            if type(plan[key]).__name__ == 'list':  # 兼容旧版格式
                plan[key] = {'plans': plan[key], 'name': ''}
            elif plan[key]['name'] == '贸易站':
                window['btn_' + key].update('贸易站', button_color=('#4f4945', '#33ccff'))
            elif plan[key]['name'] == '制造站':
                window['btn_' + key].update('制造站', button_color=('#4f4945', '#ffcc00'))
            elif plan[key]['name'] == '发电站':
                window['btn_' + key].update('发电站', button_color=('#4f4945', '#ccff66'))
    except Exception as e:
        logger.error(e)
        println('json格式错误！')


# 写入排班表
def write_plan():
    with open(conf['planFile'], 'w', encoding='utf8') as c:
        json.dump(plan, c, ensure_ascii=False)


# 主页面
def menu():
    global window
    global buffer
    load_conf()
    sg.theme('LightBlue2')
    # --------主页
    package_type_title = sg.Text('服务器:', size=10)
    package_type_1 = sg.Radio('官服', 'package_type', default=conf['package_type'] == 1,
                              key='radio_package_type_1', enable_events=True)
    package_type_2 = sg.Radio('BiliBili服', 'package_type', default=conf['package_type'] == 2,
                              key='radio_package_type_2', enable_events=True)
    adb_title = sg.Text('adb连接地址:', size=10)
    adb = sg.InputText(conf['adb'], size=60, key='conf_adb', enable_events=True)
    # 黑名单
    free_blacklist_title = sg.Text('宿舍黑名单:', size=10)
    free_blacklist = sg.InputText(conf['free_blacklist'], size=60, key='conf_free_blacklist', enable_events=True)
    # 排班表json
    plan_title = sg.Text('排班表:', size=10)
    plan_file = sg.InputText(conf['planFile'], readonly=True, size=60, key='planFile', enable_events=True)
    plan_select = sg.FileBrowse('...', size=(3, 1), file_types=(("JSON files", "*.json"),))
    # 总开关
    on_btn = sg.Button('开始执行', key='on')
    off_btn = sg.Button('立即停止', key='off', visible=False, button_color='red')
    # 日志栏
    output = sg.Output(size=(150, 25), key='log', text_color='#808069', font=('微软雅黑', 9))

    # --------排班表设置页面
    # 宿舍区
    central = sg.Button('控制中枢', key='btn_central', size=(18, 3), button_color='#303030')
    dormitory_1 = sg.Button('宿舍', key='btn_dormitory_1', size=(18, 2), button_color='#303030')
    dormitory_2 = sg.Button('宿舍', key='btn_dormitory_2', size=(18, 2), button_color='#303030')
    dormitory_3 = sg.Button('宿舍', key='btn_dormitory_3', size=(18, 2), button_color='#303030')
    dormitory_4 = sg.Button('宿舍', key='btn_dormitory_4', size=(18, 2), button_color='#303030')
    central_area = sg.Column([[central], [dormitory_1], [dormitory_2], [dormitory_3], [dormitory_4]])
    # 制造站区
    room_1_1 = sg.Button('待建造', key='btn_room_1_1', size=(12, 2), button_color='#4f4945')
    room_1_2 = sg.Button('待建造', key='btn_room_1_2', size=(12, 2), button_color='#4f4945')
    room_1_3 = sg.Button('待建造', key='btn_room_1_3', size=(12, 2), button_color='#4f4945')
    room_2_1 = sg.Button('待建造', key='btn_room_2_1', size=(12, 2), button_color='#4f4945')
    room_2_2 = sg.Button('待建造', key='btn_room_2_2', size=(12, 2), button_color='#4f4945')
    room_2_3 = sg.Button('待建造', key='btn_room_2_3', size=(12, 2), button_color='#4f4945')
    room_3_1 = sg.Button('待建造', key='btn_room_3_1', size=(12, 2), button_color='#4f4945')
    room_3_2 = sg.Button('待建造', key='btn_room_3_2', size=(12, 2), button_color='#4f4945')
    room_3_3 = sg.Button('待建造', key='btn_room_3_3', size=(12, 2), button_color='#4f4945')
    left_area = sg.Column([[room_1_1, room_1_2, room_1_3],
                           [room_2_1, room_2_2, room_2_3],
                           [room_3_1, room_3_2, room_3_3]])
    # 功能区
    meeting = sg.Button('会客室', key='btn_meeting', size=(24, 2), button_color='#303030')
    factory = sg.Button('加工站', key='btn_factory', size=(24, 2), button_color='#303030')
    contact = sg.Button('办公室', key='btn_contact', size=(24, 2), button_color='#303030')
    right_area = sg.Column([[meeting], [factory], [contact]])

    setting_layout = [
        [sg.Column([[sg.Text('设施类别:'), sg.InputCombo(['贸易站', '制造站', '发电站'], size=12, key='station_type')]],
                   key='station_type_col', visible=False)]]
    # 排班表设置标签
    for i in range(1, 6):
        set_area = sg.Column([[sg.Text('干员：'),
                               sg.InputCombo(['Free'] + agent_list, size=20, key='agent' + str(i)),
                               sg.Text('组：'),
                               sg.InputText('', size=15, key='group' + str(i)),
                               sg.Text('替换：'),
                               sg.InputText('', size=30, key='replacement' + str(i))
                               ]], key='setArea' + str(i), visible=False)
        setting_layout.append([set_area])
    setting_layout.append([sg.Button('保存', key='savePlan', visible=False)])
    setting_area = sg.Column(setting_layout, element_justification="center",
                             vertical_alignment="bottom",
                             expand_x=True)

    # --------高级设置页面
    ling_xi_title = sg.Text('令夕模式（令夕上班时起作用）：', size=25)
    ling_xi_1 = sg.Radio('感知信息', 'ling_xi', default=conf['ling_xi'] == 1,
                         key='radio_ling_xi_1', enable_events=True)
    ling_xi_2 = sg.Radio('人间烟火', 'ling_xi', default=conf['ling_xi'] == 2,
                         key='radio_ling_xi_2', enable_events=True)
    ling_xi_3 = sg.Radio('均衡模式', 'ling_xi', default=conf['ling_xi'] == 3,
                         key='radio_ling_xi_3', enable_events=True)
    rest_in_full_title = sg.Text('需要回满心情的干员：', size=25)
    rest_in_full = sg.InputText(conf['rest_in_full'], size=60,
                                key='conf_rest_in_full', enable_events=True)
    # mail
    mail_enable_1 = sg.Radio('启用', 'mail_enable', default=conf['mail_enable'] == 1,
                             key='radio_mail_enable_1', enable_events=True)
    mail_enable_0 = sg.Radio('禁用', 'mail_enable', default=conf['mail_enable'] == 0,
                             key='radio_mail_enable_0', enable_events=True)
    account_title = sg.Text('QQ邮箱', size=25)
    account = sg.InputText(conf['account'], size=60, key='conf_account', enable_events=True)
    pass_code_title = sg.Text('授权码', size=25)
    pass_code = sg.Input(conf['pass_code'], size=60, key='conf_pass_code', enable_events=True, password_char='*')
    mail_frame = sg.Frame('邮件提醒',
                          [[mail_enable_1, mail_enable_0], [account_title, account], [pass_code_title, pass_code]])
    # maa

    maa_enable_1 = sg.Radio('启用', 'maa_enable', default=conf['maa_enable'] == 1,
                            key='radio_maa_enable_1', enable_events=True)
    maa_enable_0 = sg.Radio('禁用', 'maa_enable', default=conf['maa_enable'] == 0,
                            key='radio_maa_enable_0', enable_events=True)
    maa_path_title = sg.Text('MAA地址', size=25)
    maa_path = sg.InputText(conf['maa_path'], size=60, key='conf_maa_path', enable_events=True)
    maa_adb_path_title = sg.Text('adb地址', size=25)
    maa_adb_path = sg.InputText(conf['maa_adb_path'], size=60, key='conf_maa_adb_path', enable_events=True)
    maa_weekly_plan_title = sg.Text('周计划', size=25)
    maa_layout = [[maa_enable_1, maa_enable_0], [maa_path_title, maa_path], [maa_adb_path_title, maa_adb_path],
                  [maa_weekly_plan_title]]
    for i, v in enumerate(conf['maa_weekly_plan']):
        maa_layout.append([
            sg.Text(f"-- {v['weekday']}:", size=15),
            sg.Text('关卡:', size=5),
            sg.InputText(",".join(v['stage']), size=15, key='maa_weekly_plan_stage_' + str(i), enable_events=True),
            sg.Text('理智药:', size=10),
            sg.Spin([l for l in range(0, 999)], initial_value=v['medicine'], size=5,
                    key='maa_weekly_plan_medicine_' + str(i), enable_events=True, readonly=True)
        ])

    maa_frame = sg.Frame('MAA', maa_layout)
    # --------组装页面
    main_tab = sg.Tab('  主页  ', [[package_type_title, package_type_1, package_type_2],
                                 [adb_title, adb],
                                 [free_blacklist_title, free_blacklist],
                                 [plan_title, plan_file, plan_select],
                                 [output],
                                 [on_btn, off_btn]])

    plan_tab = sg.Tab('  排班表 ', [[left_area, central_area, right_area], [setting_area]], element_justification="center")

    setting_tab = sg.Tab('  高级设置 ',
                         [[ling_xi_title, ling_xi_1, ling_xi_2, ling_xi_3], [rest_in_full_title, rest_in_full],
                          [mail_frame], [maa_frame]])
    window = sg.Window('Mower', [[sg.TabGroup([[main_tab, plan_tab, setting_tab]], border_width=0,
                                              tab_border_width=0, focus_color='#bcc8e5',
                                              selected_background_color='#d4dae8', background_color='#aab6d3',
                                              tab_background_color='#aab6d3')]], font='微软雅黑', finalize=True,
                       resizable=True)

    load_plan(conf['planFile'])
    btn = None
    while True:
        event, value = window.Read()

        if event == sg.WIN_CLOSED:
            break
        elif event.startswith('conf_'):
            key = event[5:]
            conf[key] = window[event].get()
        elif event.startswith('radio_'):
            v_index = event.rindex('_')
            conf[event[6:v_index]] = int(event[v_index + 1:])
        elif event == 'planFile' and plan_file.get() != conf['planFile']:  # 排班表
            write_plan()
            load_plan(plan_file.get())
            plan_file.update(conf['planFile'])
        elif event.startswith('maa_weekly_plan_stage_'):  # 关卡名
            v_index = event.rindex('_')
            conf['maa_weekly_plan'][int(event[v_index + 1:])]['stage'] = [window[event].get()]
        elif event.startswith('maa_weekly_plan_medicine_'):  # 体力药
            v_index = event.rindex('_')
            conf['maa_weekly_plan'][int(event[v_index + 1:])]['medicine'] = int(window[event].get())
        elif event.startswith('btn_'):  # 设施按钮
            btn = event
            init_btn(event)
        elif event == 'savePlan':  # 保存设施信息
            save_btn(btn)

        elif event == 'on':
            if adb.get() == '':
                println('adb未设置！')
                continue

            on_btn.update(visible=False)
            off_btn.update(visible=True)
            clear()
            parent_conn, child_conn = Pipe()
            main_thread = Process(target=main, args=(conf, plan, child_conn), daemon=True)
            main_thread.start()
            window.perform_long_operation(lambda: log(parent_conn), 'log')
        elif event == 'off':
            println('停止运行')
            child_conn.close()
            main_thread.terminate()
            on_btn.update(visible=True)
            off_btn.update(visible=False)

    window.close()
    write_conf()
    write_plan()


def init_btn(event):
    room_key = event[4:]
    station_name = plan[room_key]['name'] if room_key in plan.keys() else ''
    plans = plan[room_key]['plans'] if room_key in plan.keys() else []
    if room_key.startswith('room'):
        window['station_type_col'].update(visible=True)
        window['station_type'].update(station_name)
        visible_cnt = 3  # 设施干员需求数量
    else:
        if room_key == 'meeting':
            visible_cnt = 2
        elif room_key == 'factory' or room_key == 'contact':
            visible_cnt = 1
        else:
            visible_cnt = 5
        window['station_type_col'].update(visible=False)
        window['station_type'].update('')
    window['savePlan'].update(visible=True)
    for i in range(1, 6):
        if i > visible_cnt:
            window['setArea' + str(i)].update(visible=False)
            window['agent' + str(i)].update('')
            window['group' + str(i)].update('')
            window['replacement' + str(i)].update('')
        else:
            window['setArea' + str(i)].update(visible=True)
            window['agent' + str(i)].update(plans[i - 1]['agent'] if len(plans) >= i else '')
            window['group' + str(i)].update(plans[i - 1]['group'] if len(plans) >= i else '')
            window['replacement' + str(i)].update(','.join(plans[i - 1]['replacement']) if len(plans) >= i else '')


def save_btn(btn):
    plan1 = {'name': window['station_type'].get(), 'plans': []}
    for i in range(1, 6):
        agent = window['agent' + str(i)].get()
        group = window['group' + str(i)].get()
        replacement = list(filter(None, window['replacement' + str(i)].get().replace('，', ',').split(',')))
        if agent != '':
            plan1['plans'].append({'agent': agent, 'group': group, 'replacement': replacement})
        elif btn.startswith('btn_dormitory'):  # 宿舍
            plan1['plans'].append({'agent': 'Free', 'group': '', 'replacement': []})
    plan[btn[4:]] = plan1
    write_plan()
    load_plan(conf['planFile'])


# 输出日志
def log(pipe):
    try:
        while True:
            msg = pipe.recv()
            println(msg)
    except EOFError:
        pipe.close()


def println(msg):
    global buffer
    global line
    global half_line_index
    maxLen = 500  # 最大行数
    buffer = f'{buffer}\n{time.strftime("%m-%d %H:%M:%S")} {msg}'.strip()
    window['log'].update(value=buffer)
    if line == maxLen // 2:
        half_line_index = len(buffer)
    if line >= maxLen:
        buffer = buffer[half_line_index:]
        line = maxLen // 2
    else:
        line += 1


# 清空输出栏
def clear():
    global buffer
    global line
    buffer = ''
    window['log'].update(value=buffer)
    line = 0


if __name__ == '__main__':
    freeze_support()
    menu()
