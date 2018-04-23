#!/usr/bin/env python
# -*- coding: utf8 -*-

HTML_BANS = u"""
<div>
    <table style="width:100%;">
        <tr>
            <td><label class="control-label">{stat}</label></td>
            <td>{ban}</td>
        </tr>
        <tr>
            <td><label class="control-label">{lift_at}</label></td>
            <td>{alter}</td>
        </tr>
        <tr>
            <td colspan="2"><label class="control-label">{limits}</label></td>
        </tr>
    </table>
</div>

<div class="wxAlter" id="user_bans">
    <div class="wxAlterInner">
    <input type="hidden" id="user_id" value="{uid}">
    <input type="hidden" id="user_nickname" value="{uname}">
    <table>
        <tr>
            <td colspan="3"><label class="control-label">请选择封号时长</label></td>
        </tr>
        <tr>
            <td><input type="radio" name="ban_time" value="0" checked="checked">一周</td>
            <td><input type="radio" name="ban_time" value="1">15天</td>
        </tr>
        <tr>
            <td><input type="radio" name="ban_time" value="2">半年</td>
            <td><input type="radio" name="ban_time" value="3">永久</td>
            <td><input type="radio" name="ban_time" value="4">
                自定义：<input type="number" id="ban_days" min="1" value="1">天</td>
        </tr>
        <tr>
            <td colspan="3">
                <label class="control-label">请选择限制条件（可多选）</label>
            </td>
        </tr>
        <tr>
            <td colspan="3">
                <input type="checkbox" name="limit" value="0">禁止开直播
            </td>
        </tr>
        <tr>
            <td colspan="3">
                <input type="checkbox" name="limit" value="1">禁止上传视频
            </td>
        </tr>
        <tr>
            <td colspan="3">
                <input type="checkbox" name="limit" value="2">禁止发评论/弹幕
            </td>
        </tr>
        <tr>
            <td colspan="3">
                <input type="checkbox" name="limit" value="3">禁止私信
            </td>
        </tr>
        <tr>
            <td colspan="3">
                <input type="checkbox" name="limit" value="4">禁止登录
            </td>
        </tr>
        <tr>
            <td colspan="3"><label class="control-label">请输入封号原因</label></td>
        </tr>
        <tr>
            <td colspan="3">
                <textarea id="ban_reason"></textarea>
            </td>
        </tr>
        <tr>
            <td><button class="btn btn-default" type="button"
                onclick="save_bans();">封禁</button></td>
            <td><button class="btn btn-default" type="button"
                onclick="hide_bans_page();">关闭</button></td>
        </tr>
    </table>
    </div>
</div>

<script>
    function show_bans_page(){{
        $("#user_bans").show()
    }}

    function hide_bans_page(){{
        $("#user_bans").hide()
    }}

    function lift_user(){{
        if(confirm("确定对用户解除封禁？")){{
            $("#status").val(0);
            $("form")[0].submit();
        }}
    }}

    function save_bans(){{
        var user_id = $("#user_id").val();
        var day_choice = $("input:radio[name='ban_time']:checked").val();
        var ban_days = $("#ban_days").val();
        //alert(day_choice);
        var limits = [];
        $("input:checkbox[name='limit']:checked").each(function(){{
            limits.push($(this).val());
        }});
        //alert(limits);
        if(limits.length == 0){{
            alert("至少要选择一项限制条件！");
            return;
        }}
        var reason = $("#ban_reason").val();
        if(! reason){{
            alert("请输入封号理由！");
            return;
        }}
        //alert(reason);
        var days = ["7天", "15天", "6个月", "永久"];
        var days_text = "";
        if(day_choice < 4){{
            days_text = days[day_choice];
        }}
        else{{
            days_text = ban_days+"天";
        }}
        var msg = "确定要对用户'"+$("#user_nickname").val()+"'实施"+days_text+"封禁?";
        if(! confirm(msg))return;

        $.ajax({{
            type: 'POST',
            url: '/admin/videoreport/ban/' ,
            data: {{"user_id": user_id, "day_choice": day_choice,
                    "ban_days": ban_days, "limits": limits, "reason":reason}},
            dataType:"json",
            success: function (resp) {{
                if(resp.status != 0){{
                    alert(resp.errmsg);
                    return
                }}
                alert("账户已被封禁！");
                window.location.reload();
            }}
        }});
    }}

    document.getElementsByClassName("form-group")[8].style.display = "none";

</script>

<style>
    .wxAlter{{display: none; width: 100%; height: 100%; position: fixed;
            background:rgba(0,0,0,0.6); z-index: 9999; top: 0px; left: 0px;}}
    .wxAlterInner{{position: absolute; width: 600px; background: #fff;
            top:150px; left:50%; margin-left:-300px; padding: 20px 30px;}}
    .wxAlterInner table{{width: 100%; height: 100%; margin: auto;}}
    .wxAlterInner textarea{{width: 100%; min-height: 100px;}}
    .wxAlterInner button{{margin-top: 10px;}}
</style>
"""