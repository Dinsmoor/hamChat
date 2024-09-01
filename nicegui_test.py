import datetime
from nicegui import ui
# this uses tailwind css for styling, in the .classes() method you can add any tailwind css class

ui.page_title('hamChat')
dark = ui.dark_mode()
dark.enable()

mail_messages = [
    {'from': 'K7OOO', 'date': datetime.datetime.now(), 'subject': 'Test mail 1', 'body': 'This is the body of the first test mail'},
    {'from': 'KJ7PPP', 'date': datetime.datetime.now(), 'subject': 'Test mail 2', 'body': 'This is the body of the second test mail'},
]

def make_chat_tab():
    chat_messages = []
    for i in range(10):
        txt = f'This is chat message {i}' if i % 2 == 0 else f'This is chat message {i} with a longer text to test the wrapping aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        snt = False if i % 2 == 0 else True
        nme = 'K7OOO' if i % 2 == 0 else 'KJ7PPP'
        msg = ui.chat_message(text=txt,
                        name=nme,
                        stamp=datetime.datetime.now().strftime('%H:%M:%S'),
                        sent=snt,
                        ).classes('justify-center max-w-prose')
        chat_messages.append(msg)

def make_mail_tab():
    # sorting button
    # with ui.row().classes('mx-auto my-auto justify-center'):
    #     ui.label('Sort by:')
    #     ui.select(['Date', 'From', 'Subject'], value='Date')
    #     ui.label('Show:')
    #     ui.select(['All', 'Outgoing', 'Sent', 'Received'], value='All')
    columns = [
        {'name': 'messageid', 'label': 'Message ID', 'field': 'messageid'},
        {'name': 'date', 'label': 'Date', 'field': 'date'},
        {'name': 'to', 'label': 'To', 'field': 'to'},
        {'name': 'subject', 'label': 'Subject', 'field': 'subject'},

    ]
    mail_content = "Skibidi gyatt ohio rizzler fanum tax for when the backrooms griddy is uncanny, but the sussy baka meme is actually a low-key flex, and the cringe normie squad is hella toxic, so let's vibe and flex on those haters with some epic drip, while we're suspending disbelief for the sake of this meta-af plot twist that's totally lit, and don't even get me started on the algorithm's uncanny valley vibes, especially when the AI starts dropping knowledge bombs like a woke shaman."
    rows = [
        {'name': 'Alice', 'date': datetime.datetime.now().strftime('%D %H:%M'), 'body': mail_content, 'to': 'K7OOO', 'subject': 'Test mail 1', 'messageid': '12ET245BT34'},
        {'name': 'Bob', 'date': datetime.datetime.now().strftime('%D %H:%M'), 'body': mail_content, 'to': 'KJ7PPP', 'subject': 'Test mail 2', 'messageid': '567WRBREB8'},
        {'name': 'Carol', 'date': datetime.datetime(2022, 1, 22).strftime('%D %H:%M'), 'body': mail_content , 'to': 'KJ7PPP', 'subject': 'Test mail 2', 'messageid': '56RTBWBTR78'},
    ]

    table = ui.table(columns=columns, rows=rows, row_key='name').classes('min-w-80 max-w-5xl mx-auto my-auto max-w-fit')
    table.add_slot('header', r'''
        <q-tr :props="props">
            <q-th auto-width />
            <q-th v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.label }}
            </q-th>
        </q-tr>
    ''')
    table.add_slot('body', r'''
        <q-tr :props="props">
            <q-td auto-width>
                <q-btn size="sm" color="accent" round dense
                    @click="props.expand = !props.expand"
                    :icon="props.expand ? 'remove' : 'add'" />
            </q-td>
            <q-td v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.value }}
            </q-td>
        </q-tr>
        <q-tr v-show="props.expand" :props="props">
            <q-td colspan="100%">
                <div class="text-left">Message ID:{{ props.row.messageid }}</div>
                <div class="text-left">To:{{ props.row.to }}</div>
                <div class="text-left">Subject:{{ props.row.subject }}</div>
                <div class="text-left">Date:{{ props.row.date }}</div>
                <div class="text-left">From:{{ props.row.name }}</div>
                <div class="text-left">Message:</div><br>
                <div class="text-left max-w-prose" style="white-space: normal;">{{ props.row.body }}</div>
                
            </q-td>
        </q-tr>
    ''')
                
            
def make_plugins_tab():
    for i in range(10):
        with ui.expansion(f"Plugin {i}", icon='plug'):
            ui.label(f'This is plugin {i}')

def make_settings_tab():
    for i in range(10):
        with ui.expansion(f"Setting {i}", icon='cog', group='settings'):
            ui.label(f'This is baloney setting menu {i}')
            ui.radio(['one', 'Option 2', 'Option 3'], value='one').props('inline')

# top row of buttons for tabbed navigation
with ui.header():
    with ui.tabs().classes('w-screen static') as tabs:
        chat = ui.tab('Chat')
        mail = ui.tab('Mail')
        plugins = ui.tab('Plugins')
        settings = ui.tab('Settings')
with ui.tab_panels(tabs, value=mail).classes(' mx-auto my-auto justify-center'):
    with ui.tab_panel(chat):
        make_chat_tab()
    with ui.tab_panel(mail):  
        make_mail_tab()
    with ui.tab_panel(plugins):
        make_plugins_tab()
    with ui.tab_panel(settings):
        make_settings_tab()

ui.run(port=8009)