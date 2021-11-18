from pydantic import BaseModel
from os import getenv
from datetime import datetime, timedelta
from threading import Timer

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from requests import post
from dotenv import load_dotenv

load_dotenv()

discord_hook = getenv("COMMON_ROOM_WEBHOOK")
max_members = int(getenv("MAX_MEMBERS"))
max_time = int(getenv("MAX_TIME"))


class CommonRoomSchema(BaseModel):
    name: str


class MembersList(dict):
    def add(self, key, value):
        self[key] = value

    def delete(self, key):
        del self[key]


class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


app = FastAPI()
current_members = MembersList()


@app.post("/signin")
def common_room_signin(member: CommonRoomSchema):
    if member.name in current_members or len(current_members) < max_members:
        current_members.add(member.name, datetime.now())
        webhook_data = {"content": f"{member.name} has just signed in to the common room, {len(current_members)}"
                                   f"/{max_members} members currently signed in"}
        post(discord_hook, data=webhook_data)
        return {
            "code": "200",
            "message": f"{member.name} successfully signed in"
        }
    else:
        return {
            "code": "403",
            "message": f"Could not sign {member.name} in to common room, too many people currently in the room"
        }


@app.post("/signout")
def common_room_signout(member: CommonRoomSchema):
    if member.name in current_members:
        current_members.delete(member.name)
        webhook_data = {"content": f"{member.name} has just signed out of the common room, {len(current_members)}"
                                   f"/{max_members} members currently signed in"}
        post(discord_hook, data=webhook_data)
        return {
            "code": "200",
            "message": f"{member.name} successfully signed out"
        }
    return {
        "code": "404",
        "message": f"{member.name} not signed in to common room"
    }


@app.get("/signin", response_class=HTMLResponse)
def signin_page():
    return open("html/signin-form.html", "r").read()


@app.get("/signout", response_class=HTMLResponse)
def signout_page():
    return open("html/signin-form.html", "r").read()


@app.get("/img/redbrick", response_class=FileResponse)
def redbrick_img():
    return FileResponse("assets/redbrick.png")


@app.get("/favicon.ico", response_class=FileResponse)
def redbrick_img():
    return FileResponse("assets/redbrick.png")


@app.get("/img/engineering", response_class=FileResponse)
def engineering_img():
    return FileResponse("assets/engineering.png")


def check_members():
    for member in list(current_members.keys()):
        if current_members[member] < datetime.now() - timedelta(seconds=max_time):
            webhook_data = {"content": f"{member}'s time has expired, please sign back in or leave the common room"}
            post(discord_hook, data=webhook_data)
            current_members.delete(member)


rt = RepeatedTimer(5, check_members)
