import aiohttp


def connection(func):
    async def inner(*args, **kwargs):
        async with aiohttp.ClientSession() as session:
            return await func(session, *args, **kwargs)

    return inner
@connection
async def get_all_available_projects(session, url, headers):
    async with session.get(url + "/projects", headers=headers) as response:
        return await response.json()
@connection
async def get_project(session, url, project_id, headers):
    async with session.get(url + "/projects/" + str(project_id), headers=headers) as response:
        return await response.json()
@connection
async def task_changing(session, url, payload, task_id, headers):
    async with session.post(url + '/tasks/' + str(task_id), json=payload, headers=headers) as response:
        return await response.json()
@connection
async def get_task(session, url, task_id, headers):
    async with session.get(url + "/tasks/"+ str(task_id), headers=headers) as response:
        return await response.json()
@connection
async def get_buckets(session, url, project_id, headers):
    async with session.get(url + "/projects/"+ str(project_id) + "/buckets", headers=headers) as response:
        return await response.json()
