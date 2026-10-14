"""Companion expeditions: one durable reward per dispatched task, even offline."""
import copy
from datetime import datetime, timedelta

ROUTES = {
    'park': {'name':'公园散步','seconds':60,'xp':5,'item':'干粮','count':1,'story':'沿着草地走了一圈，遇见一位分享干粮的邻居。'},
    'woods': {'name':'林间采集','seconds':300,'xp':15,'item':'树枝','count':2,'story':'在林间听了很久的鸟鸣，带回两根适合布置小窝的树枝。'},
    'ruins': {'name':'旧城探索','seconds':900,'xp':35,'item':'石片','count':2,'story':'走过旧城拱门，把发现的石片收进背包，记住了回家的路。'},
}

class PetGame:
    def __init__(self, store, lock, clock=datetime.now):
        self.store,self.lock,self.clock=store,lock,clock

    def commit(self, state):
        self.store.save(state)
        self.store.state=state

    def settle(self):
        task=self.store.state['pet_game']['task']
        if not task or self.clock()<datetime.fromisoformat(task['due']):return
        updated=copy.deepcopy(self.store.state)
        game=updated['pet_game']
        game['xp']+=task['xp']
        game['materials'][task['item']]+=task['count']
        updated['pet']['affinity']+=1
        game['log'].insert(0,{'time':task['due'],'text':f"{task['name']}完成：{task['story']} 获得 {task['xp']} 经验和 {task['count']} 份{task['item']}。"})
        game['log']=game['log'][:50]
        game['task']=None
        self.commit(updated)

    def snapshot(self):
        with self.lock:
            try:self.settle()
            except OSError:return {'ok':False,'error':'任务结算保存失败，奖励尚未确认，请检查目录权限。'}
            game=copy.deepcopy(self.store.state['pet_game'])
            task=game['task']
            remaining=max(0,int((datetime.fromisoformat(task['due'])-self.clock()).total_seconds())) if task else 0
            return {'ok':True,'name':self.store.state['pet']['name'],'affinity':self.store.state['pet']['affinity'],
                'level':1+game['xp']//100,'game':game,'remaining':remaining,'routes':ROUTES}

    def dispatch(self, route):
        with self.lock:
            if not isinstance(route,str) or route not in ROUTES:return {'ok':False,'error':'请选择有效路线。'}
            try:
                self.settle()
                if self.store.state['pet_game']['task']:return {'ok':False,'error':'伙伴还在路上，一次只出发一趟。'}
                updated=copy.deepcopy(self.store.state)
                updated['pet_game']['task']={**ROUTES[route],'route':route,'due':(self.clock()+timedelta(seconds=ROUTES[route]['seconds'])).isoformat()}
                updated['pet_game']['task']['xp']+=2*updated['pet_game']['home_level']
                self.commit(updated)
                return self.snapshot()
            except OSError:return {'ok':False,'error':'出发保存失败，请重试。'}

    def interact(self, action):
        with self.lock:
            if action not in ('pet','feed'):return {'ok':False,'error':'未知互动。'}
            now=self.clock()
            game=self.store.state['pet_game']
            if action=='feed' and game['materials']['干粮']<1:return {'ok':False,'error':'干粮用完了，公园散步可以带回干粮。'}
            last=game.get('last_'+action)
            if last and (now-datetime.fromisoformat(last)).total_seconds()<60:return {'ok':False,'error':'刚刚互动过，等一分钟再来吧。'}
            updated=copy.deepcopy(self.store.state)
            updated['pet_game']['last_'+action]=now.isoformat()
            if action=='feed':updated['pet_game']['materials']['干粮']-=1
            updated['pet']['affinity']+=2 if action=='feed' else 1
            try:self.commit(updated)
            except OSError:return {'ok':False,'error':'互动保存失败，没有扣除物品。'}
            return self.snapshot()

    def upgrade_home(self):
        with self.lock:
            level=self.store.state['pet_game']['home_level']
            if level>=5:return {'ok':False,'error':'小窝已经达到 5 级。'}
            costs={'树枝':2*(level+1),'石片':level+1}
            materials=self.store.state['pet_game']['materials']
            if any(materials[name]<count for name,count in costs.items()):
                return {'ok':False,'error':f"升级需要 {costs['树枝']} 份树枝和 {costs['石片']} 份石片，去采集和探索吧。"}
            updated=copy.deepcopy(self.store.state)
            for name,count in costs.items():updated['pet_game']['materials'][name]-=count
            updated['pet_game']['home_level']+=1
            try:self.commit(updated)
            except OSError:return {'ok':False,'error':'小窝保存失败，没有扣除材料。'}
            return self.snapshot()
