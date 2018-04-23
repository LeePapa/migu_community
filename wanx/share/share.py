# -*- coding: utf8 -*-
from flask import Blueprint, render_template, request
from flask import abort
from wanx.models.video import Video
from wanx.models.comment import Comment
from wanx import app

import time


share = Blueprint("share", __name__, url_prefix="/share",
                  template_folder="templates")


def stamp_str(stamp):
    ltime = time.localtime(int(stamp))
    return time.strftime("%Y-%m-%d %H:%M:%S", ltime)


@share.route("/page/<string:vid>", methods=("GET",))
def share_page(vid):
    video = Video.get_one(vid)
    if not video:
        abort(404)

    cids = Comment.video_comment_ids(vid, 1, 10)
    comments = [c.format() for c in Comment.get_list(cids)]

    vids = Video.game_hotvideo_ids(str(video.game), 1, 10)
    recommend_videos = [v.format() for v in Video.get_list(vids)]

    video = video.format()
    _from = request.values.get('ywfrom', None)
    mgyxdt_url = 'http://g.10086.cn/s/clientd/?t=GH_JFDX'
    download_url = video['game']['url'] if _from != 'miguyouxidating' else mgyxdt_url
    video_dict = {
        "nick_name": video['author'] and video['author']['nickname'],
        "user_logo": video['author'] and video['author']['logo'],
        "title": video['title'],
        "description": video['title'],
        "created_time": stamp_str(video['create_at']),
        "url": str(video['url']),
        "image_url": str(video['cover']),
        "favour": video.get("like_count", "0"),
        "comment": video['comment_count'],
        "vv": video['vv'],
        "game_download_url": download_url,
        "game_logo": video['game'] and video['game']['icon'],
        "game_name": video['game'] and video['game']['name'],
        "game_description": video['game'] and video['game']['description'],
        "game_video_count": video['game'] and video['game']['video_count'],
        "app_logo": video['game']['icon'],
    }

    comments_list = []
    for c in comments:
        comments_list.append({
            "nick_name": c['author'] and c['author']['nickname'],
            "user_icon": c['author'] and c['author']['logo'],
            "created_at": stamp_str(c['create_at']),
            "content": c['content'],
            "favour": c['like']
        })

    recommend_videos_list = []
    for v in recommend_videos:
        recommend_videos_list.append({
            "share_url": v['share_url'],
            "title": v['title'],
            "image_url": v['cover'],
            "video_id": v['video_id'],
            "vv": v['vv']
        })

    return render_template("share.html",
                           static_url=app.config['STATIC_URL'],
                           video=video_dict,
                           comments=comments_list,
                           recommends=recommend_videos_list,
                           ywfrom=_from)
