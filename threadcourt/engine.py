"""Bounded exhaustive exploration of explicit concurrency models, not arbitrary code."""
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class State:
    pc: tuple = (0, 0)
    value: int = 0
    registers: tuple = (0, 0)
    owners: tuple = (-1, -1)


SCENARIOS = {
    'lost-update': {'title': 'Lost update', 'description': 'Two workers read, increment and write one shared counter.',
                    'repair': 'Protect the entire read-modify-write with a single lock.'},
    'lock-inversion': {'title': 'Lock inversion', 'description': 'Two workers acquire the same pair of locks in opposite orders.',
                       'repair': 'Acquire both locks in the same global order in every worker.'},
}


def transitions(state, scenario, fixed=False):
    if scenario not in SCENARIOS:
        raise ValueError('Unknown scenario')
    for tid in range(2):
        pc = list(state.pc)
        regs = list(state.registers)
        owners = list(state.owners)
        value = state.value
        stage = pc[tid]
        if scenario == 'lost-update':
            if stage == 3:
                continue
            if fixed and stage == 0 and owners[0] not in (-1, tid):
                continue
            if stage == 0:
                if fixed:
                    owners[0] = tid
                regs[tid] = value
                action = f'read counter={value}'
            elif stage == 1:
                regs[tid] += 1
                action = f'increment local={regs[tid]}'
            else:
                value = regs[tid]
                if fixed:
                    owners[0] = -1
                action = f'write counter={value}'
        else:
            if stage == 4:
                continue
            order = (0, 1) if fixed or tid == 0 else (1, 0)
            lock = order[stage if stage < 2 else 3-stage]
            if stage < 2:
                if owners[lock] != -1:
                    continue
                owners[lock] = tid
                action = f'acquire L{lock}'
            else:
                if owners[lock] != tid:
                    raise RuntimeError('Invalid ownership')
                owners[lock] = -1
                action = f'release L{lock}'
        pc[tid] += 1
        yield tid, action, State(tuple(pc), value, tuple(regs), tuple(owners))


def complete(state, scenario):
    return all(p == (3 if scenario == 'lost-update' else 4) for p in state.pc)


def explore(scenario, fixed=False, max_states=10000):
    if scenario not in SCENARIOS:
        raise ValueError('Unknown scenario')
    if not 1 <= max_states <= 100000:
        raise ValueError('max_states must be between 1 and 100000')
    queue = deque([(State(), [])])
    seen = {State()}
    violation = None
    terminal = 0
    truncated = False
    while queue:
        state, trace = queue.popleft()
        moves = list(transitions(state, scenario, fixed))
        done = complete(state, scenario)
        if done:
            terminal += 1
        failure = ('lost-update' if done and scenario == 'lost-update' and state.value != 2
                   else 'deadlock' if not done and not moves else None)
        if failure and violation is None:
            violation = {'kind': failure, 'trace': trace, 'final_value': state.value}
        for tid, action, nxt in moves:
            if nxt in seen:
                continue
            if len(seen) >= max_states:
                truncated = True
                continue
            seen.add(nxt)
            queue.append((nxt, trace + [{'thread': tid, 'action': action, 'pc': list(nxt.pc),
                                        'value': nxt.value, 'owners': list(nxt.owners)}]))
    return {'scenario': scenario, 'fixed': fixed, 'states': len(seen), 'terminal_states': terminal,
            'exhaustive': not truncated, 'violation': violation,
            'verdict': 'violation-found' if violation else 'inconclusive' if truncated else 'no-violation-in-model'}


def replay(scenario, trace, fixed=False):
    state = State()
    for event in trace:
        matches = [(action, nxt) for tid, action, nxt in transitions(state, scenario, fixed)
                   if tid == event['thread']]
        if len(matches) != 1:
            raise ValueError('Schedule contains a blocked or completed thread')
        action, state = matches[0]
        actual = {'thread': event['thread'], 'action': action, 'pc': list(state.pc),
                  'value': state.value, 'owners': list(state.owners)}
        if actual != event:
            raise ValueError('Trace differs from model execution')
    return state
