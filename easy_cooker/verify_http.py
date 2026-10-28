"""Exercise a running main.py server using only HTTP requests."""
import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--table', type=int, default=1, help='Use a currently unoccupied table')
    parser.add_argument('--complete-task', help='Complete this task instead of submitting orders')
    parser.add_argument('--chef', type=int, default=1)
    args = parser.parse_args()
    base = args.base_url.rstrip('/')

    def call(method, path, body=None):
        request = Request(base + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=5) as response:
                result = json.load(response)
        except HTTPError as exc:
            with exc:
                detail = exc.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'{method} {path}: HTTP {exc.code}: {detail}') from exc
        print(f'\n{method} {path}')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    try:
        if args.complete_task:
            call('POST', f'/chefs/{args.chef}/tasks/{args.complete_task}/complete')
            call('GET', f'/chefs/{args.chef}/task')
            return 0
        health = call('GET', '/health')
        if health.get('status') != 'ok':
            raise RuntimeError('Unexpected health response')
        menu = call('GET', '/menu')
        # Pick the quickest dish so the subsequent manual completion takes less time.
        dish = min(menu, key=lambda item: item['duration_seconds'])
        token = uuid4().hex
        request = {'request_id': f'verify-{token}', 'table_id': args.table,
                   'items': [{'dish_id': dish['id'], 'quantity': 1}]}
        accepted = call('POST', '/orders', request)
        retry = call('POST', '/orders', request)
        if retry != accepted:
            raise RuntimeError('Idempotent retry returned a different result')
        session_id = accepted['session_id']
        call('POST', '/orders', {'request_id': f'verify-add-{token}',
            'table_id': args.table, 'session_id': session_id,
            'items': [{'dish_id': dish['id'], 'quantity': 1}]})
        session = call('GET', f'/sessions/{session_id}')
        if len(session['demands']) != 2:
            raise RuntimeError('Expected exactly two portions after retry and addition')
        state = call('GET', '/state')
        print('\n验证通过：服务可连接，下单、重复请求去重和加菜均正常。')
        print(f'本次会话：{session_id}；脚本实际新增了两份菜，尚未关闭会话。')
        found = False
        for chef in state['chefs']:
            task = chef['task']
            if task and task['session_id'] == session_id:
                found = True
                print(f"\n当前任务需制作 {dish['duration_seconds']} 秒；到时执行：")
                print(f'python3 verify_http.py --base-url {base} '
                      f"--chef {chef['chef_id']} --complete-task {task['id']}")
        if not found:
            print('本桌正在等待；请通过 GET /state 查询后续任务。')
        print('完成反馈会自动分配下一道菜；使用返回的新任务编号继续完成。')
        print(f'全部完成后关闭会话：curl -X POST {base}/sessions/{session_id}/close')
        return 0
    except (RuntimeError, URLError, TimeoutError, ValueError) as exc:
        print(f'\n验证失败：{exc}', file=sys.stderr)
        print('请检查服务地址，并使用 --table 指定空闲桌号。', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
