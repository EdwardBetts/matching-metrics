import numpy as np
import networkx as nx
import itertools
import sys
import argparse
import time
# project code
import dsd
import apxgi
import graphGen
import ppiGen

def announce(message):
    print ('{} {}'.format(time.strftime('%H:%M:%S'),message))
    sys.stdout.flush()

def createGraph(gtype, n, p, ppitype):
    if (gtype == 'ER'):
        return nx.erdos_renyi_graph(n, p)
    elif (gtype == 'BA'):
        return nx.barabasi_albert_graph(n, int(p * n))
    elif (gtype == 'WS'):
        return nx.connected_watts_strogatz_graph(n, 8, p)
    elif (gtype == 'GEO'):
        return graphGen.geoGraphP(n, 3, p)
    elif (gtype == 'VZ'):
        # Vazquez recommends p = 0.1, q = 0.7
        # Gibson suggests p = 0.24, q = 0.887
        qmap = {0.1:0.7, 0.24:0.887}
        assert(p in qmap.keys())
        return graphGen.VazquezGraph(n, p, qmap[p])
    elif (gtype == 'EV'):
        qmap = {0.1:0.7, 0.24:0.887}
        assert(p in qmap.keys())
        return graphGen.EVGraph(n, p, qmap[p], n//5, 0.8)
    elif (gtype == 'SL'):
        # values from Sole paper
        return graphGen.SoleGraph(n, 0.53, 0.06)
    elif (gtype == 'PPI'):
        return ppiGen.ppiGraph(n, ppitype)
    else:
        raise ValueError('Invalid graph type')

if __name__ == '__main__':

    if sys.version_info[0] < 3 or sys.version_info[1] < 5:
        print("Requires Python 3.5 or greater.")
        sys.exit(1)

    perturbFns = {'thin': dsd.thin, 'rewire': dsd.rewire, 'randomize': dsd.randomize, 'scramble': dsd.scramble, 'noperturb' : None}

    graphTypes = ['ER', 'BA', 'WS', 'GEO', 'VZ', 'EV', 'SL', 'PPI']
    ppiTypes = ['fly', 'human', 'mouse', 'worm', 'yeast']

    parser = argparse.ArgumentParser()
    parser.add_argument('n', type=int, default=200)
    parser.add_argument('p', type=float, default=0.03)
    parser.add_argument('gtype', choices=graphTypes)
    parser.add_argument('ptype', choices=perturbFns.keys())
    parser.add_argument('parg', type=float, nargs='?', default=0.0)
    parser.add_argument('ppitype', choices=ppiTypes, nargs='?', default='human')
    parser.add_argument('steps', type=int, nargs='?', default=500)
    args = parser.parse_args()

    perturb = perturbFns[args.ptype]
    
    sample = []
    ECvals = []
    NCvals = []

    steps = args.steps

    for i, nc in zip(range(steps), np.linspace(1/(steps+1), 1, steps, endpoint=False)):
        print('{}/{}'.format(i,steps))

        # create a random graph
        # ensure we are working with the same nodeset for both graphs
        G = createGraph(args.gtype, args.n, args.p, args.ppitype)
        G.remove_edges_from(G.selfloop_edges())
        nodeList = G.nodes()
        while (len(list(nx.connected_components(G))) > 1):
            print('Skipping a disconnected graph.')
            G = createGraph(args.gtype, args.n, args.p, args.ppitype)
            G.remove_edges_from(G.selfloop_edges())
            nodeList = G.nodes()
        A = np.array(nx.adj_matrix(G,nodeList).todense())

        # optionally perturb the graph
        if (args.ptype != 'noperturb'):
            Gperturb = perturb(G, args.parg)
            while (len(list(nx.connected_components(Gperturb))) > 1):
                Gperturb = perturb(G, args.parg)
            B = np.array(nx.adj_matrix(Gperturb,nodeList).todense())
        else:
            B = A.copy()

        if (args.gtype == 'PPI'):
            dirprefix = 'ppi/'
            gtype = args.ppitype
        else:
            dirprefix = ''
            gtype = args.gtype

        try:
            correctness, EC, iters, nCands, nRejects = apxgi.ECMCMC(A, B, nc)
            # use the last n log n values as our sample
            sample.append(correctness[-iters:])
            ECvals.append(EC)
            NCvals.append(nc)
            print('rejects: {}\n****'.format(nRejects))
            if ((i % 10) == 0):
                if (args.ptype == 'noperturb'):
                    np.savez('{}noperturb/{}/raw/Raw-n{}-p{}-nc{}'.format(dirprefix,gtype,args.n,args.p,nc),  correctness=correctness, EC=EC, nc=nc, n=args.n, p=args.p, gtype=args.gtype, ppitype=args.ppitype)
                else:
                    np.savez('{}perturb/{}/raw/Raw-n{}-p{}-nc{}-{}-{}'.format(dirprefix,gtype,args.n,args.p,nc,args.ptype,args.parg),  correctness=correctness, EC=EC, nc=nc, n=args.n, p=args.p, gtype=args.gtype,ptype=args.ptype,parg=args.parg,ppitype=args.ppitype)
        except ValueError as err:
            print(err.args)

    sample = np.array(sample)
    ECvals = np.array(ECvals)
    if (args.ptype == 'noperturb'):
        np.savez('{}noperturb/{}/Run-n{}-p{}'.format(dirprefix,gtype,args.n,args.p), sample=sample, ECvals=ECvals, n=args.n, p=args.p, gtype=args.gtype, ppitype=args.ppitype)
    else:
        np.savez('{}perturb/{}/Run-n{}-p{}-{}-{}'.format(dirprefix,gtype,args.n,args.p,args.ptype,args.parg), sample=sample, ECvals=ECvals, n=args.n, p=args.p, gtype=args.gtype, ptype=args.ptype, parg=args.parg, ppitype=args.ppitype)
    t = time.process_time()
    now = time.asctime()
    print('Ended: {}\nn={}, p={}, {}, {}, steps={}, elapsed time={:.2f} secs ({:.2f} secs/step).'.format(now,args.n,args.p,gtype,args.ptype,steps,t,t/steps))
