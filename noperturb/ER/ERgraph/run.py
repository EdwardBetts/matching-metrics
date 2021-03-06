from __future__ import print_function
import numpy as np
import networkx as nx
import itertools
import sys
import argparse
import pickle

sys.path.insert(0,'..')
import apxgi

if __name__ == '__main__':

    if sys.version_info[0] < 3 or sys.version_info[1] < 5:
        print("Requires Python 3.5 or greater.")
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument('n', type=int, default=200)
    parser.add_argument('p', type=float, default=0.03)
    args = parser.parse_args()

    sample = []
    ECvals = []
    NCvals = []

    for i, nc in zip(range(200), np.linspace(0.005, 1, 200)):
        print('{}'.format(i))

        # create a random graph
        gtype = 'ER'
        G = nx.erdos_renyi_graph(args.n, args.p)
        while (len(list(nx.connected_components(G))) > 1):
            print('Skipping a disconnected graph.')
            G = nx.erdos_renyi_graph(args.n, args.p)
        A = np.array(nx.adj_matrix(G).todense())

        try:
            correctness, EC, iters, nCands, nRejects = apxgi.ECMCMC(A, A, nc)
            # use the last n log n values as our sample
            sample.append(correctness[-iters:])
            ECvals.append(EC)
            NCvals.append(nc)
            print('rejects: {}\n****'.format(nRejects))
            if ((i % 10) == 0):
                np.savez('raw/Raw-n{}-p{}-nc{}'.format(args.n,args.p,nc),  correctness=correctness, EC=EC, nc=nc, n=args.n, p=args.p, gtype=gtype)
        except ValueError as err:
            print(err.args)

    sample = np.array(sample)
    ECvals = np.array(ECvals)
    np.savez('Run-n{}-p{}'.format(args.n,args.p), sample=sample, ECvals=ECvals, n=args.n, p=args.p, gtype=gtype)
