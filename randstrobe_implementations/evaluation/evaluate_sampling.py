import os,sys
import argparse
import errno

import random
from collections import defaultdict, Counter
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except (ImportError, RuntimeError):
    print("COULD not import matplotlib")


def mkdir_p(path):
    try:
        os.makedirs(path)
        print("creating", path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def plot_histogram(x, outfolder, h, l, name, bins=50):
    # plt.bar(x.keys(), x.values())
    # plt.hist(x, density=True, bins=30)  # density=False would make counts
    plt.hist(x, density=False, bins=bins) 
    # plt.ylabel('Probability')
    plt.ylabel('Count')
    plt.xlabel('Times a genomic coordinate is sampled for strobe 2')
    plt.title('HASH: {0}, LINK: {1}'.format(h,l))
    plt.xlim(0, 50)
    plt.yscale('log')
    outfile = os.path.join(outfolder, "{0}_{1}_{2}.pdf".format(h,l, name))
    plt.savefig(outfile)
    plt.close()
    plt.cla()
    plt.clf()


def plot_histogram_distance(x, outfolder, h, l, name, bins=50):
    plt.bar(x.keys(), x.values())
    # plt.hist(x, density=False) 
    # plt.ylabel('Probability')
    plt.ylabel('Count')
    plt.xlabel('Distance between strobes')
    plt.title('HASH: {0}, LINK: {1}'.format(h,l))
    # plt.xlim(0, 50)
    # plt.yscale('log')
    outfile = os.path.join(outfolder, "{0}_{1}_{2}.pdf".format(h,l, name))
    plt.savefig(outfile)
    plt.close()
    plt.cla()
    plt.clf()

# def plot_histogram(input_csv, outfolder):
#     pd.set_option("display.precision", 8)
#     df = pd.read_csv(input_csv)

#     # df_corr = df.loc[df['read_type'] == 'corrected']
#     # df_orig = df.loc[df['read_type'] == 'original']
#     # error_rate_orig = df_orig['error_rate'].tolist()
#     # error_rate_corr = df_corr['error_rate'].tolist()

#     sampled_pos = df_orig['error_rate'].tolist()
#     # bins = [0.1*i for i in range(300)]
#     pyplot.hist(error_rate_corr, 100, range=[0, 20], alpha=0.5, label='Corrected')
#     pyplot.hist(error_rate_orig, 100, range=[0, 20], alpha=0.5, label='Original')
#     pyplot.legend(loc='upper right')
#     # pyplot.xlabel("Difference to genome (%)")
#     pyplot.xlabel("Error rate (%)")
#     pyplot.ylabel("Read count")
#     plt.savefig(os.path.join(outfolder, dataset+ "_full.eps"))
#     plt.savefig(os.path.join(outfolder, dataset+ "_full.pdf"))
#     plt.close()


def get_distance_nonuniformity(C):
    mean = sum(C.values())/len(C)
    return sum([ abs(mean - c) for c in C.values()]) / len(C)

# def get_window_correlation(p2_sampled, k = 20):
#     tot_w = 0
#     tot_bad = 0
#     for p2 in p2_sampled[:-100]: # Do not count the end of sequence where we reduce window size (there will be more degenerate cases here)
#         window = p2_sampled[p2 - k : p2]
#         # w_dist = sum([abs(p2 - prev_p2)*(1/(i+1)) for i, prev_p2 in enumerate(window[::-1])])
#         w_corr = sum([(1/(max(1,abs(p2 - prev_p2))))*((1/(i+1))**2) for i, prev_p2 in enumerate(window[::-1])])
#         if w_corr > 0.5:
#             tot_bad += 1
#         # print(w_corr)
#         tot_w += w_corr
#     return tot_bad # tot_w / len(p2_sampled)


def get_d_min(p2_sampled, n = 5, wmin = 1, wmax = 100):
    L = wmax - wmin
    E_dist = L / (n**2 - 1)
    tot_larger = 0
    print("E_dist:", E_dist)
    tot_d_min = 0
    for i in range(len((p2_sampled[:-wmax]))): # Do not count the end of sequence where we reduce window size (there will be more degenerate cases here)
        # print(p2)
        if i < n: # not defined here
            continue
        window = sorted(p2_sampled[i - n : i])

        min_dist = min([p2-p1 for p1,p2 in zip(window[:-1], window[1:]) ])
        # print(min_dist, p2, window )
        if min_dist > E_dist:
            tot_larger += 1
        # tot_d_min += 1/(max(1, min_dist))
    num_trials = len(p2_sampled[n:-wmax])
    print(tot_larger, num_trials)
    return tot_larger / num_trials # tot_d_min / len(p2_sampled[n:-wmax])

def get_clumping_metric(p2_sampled, w = 5, wmax = 100):
    # w consecutive p2 positions are all within w nucleotides of each other
    tot_bad = 0
    for i, p2 in enumerate(p2_sampled[:-wmax]):  # Do not count the end of sequence where we reduce window size (there will be more degenerate cases here)
        if i < w: # not defined here
            continue
        window = p2_sampled[i - w : i]
        if len(window) == w:
            p_min = min(window)
            p_max = max(window)
            if p_max - p_min <= w:
                tot_bad += 1   
                # if w > 5: 
                #     print(w, p2, window)
    return tot_bad

def main(args):
    """
        Aim: As direct and interprateble statistics as possible. Should be comparable.
             For example, p-values from a uniformity test, or poison statistics from times a position
             is sampled is not comparable. Instead, we give the exact average deviance from mean of histogram uniformity.
             and the total number of unique positions and the max repetitive, as well as the toral distribution.

        Metrics:
        M1: Distance uniformity distribution
        M2: Strobe 2 position sampling distribution (times a position is sampled)
        M3: Min dist: Minimum distance between M consecutive strobes.
        M4: Clump count metric: How many positions do I have where x consecutive strobes are all sampled within a total span of x bps.
    """
    sampling_distribution = {}
    p2_sampled = []
    distances_sampled = []
    for line in open(args.positions, "r"):
        # nohash,Sahlin1,contig-120_0,75,152
        h, l, ref, p1, p2 = line.strip().split(",")
        d = int(p2) - int(p1)
        p2_sampled.append(int(p2))
        distances_sampled.append(d)

    print("Hash,Link,total_unique,most_repetitive,distance_nonuniformity,d_min_5,d_max2,d_max3,d_max4,d_max5,d_max6-10")

    C1 = Counter(p2_sampled)
    unique_p2_sampled = len(C1)
    max_p2_sampled = C1.most_common(1)[0][1]
    # print(h, l, unique_p2_sampled, "most_repetitive position:", most_repetitive[1])
    plot_histogram(C1.values(), args.outfolder, h, l, "strobe_2_distribution", bins=50)

    C2 = Counter(distances_sampled)
    # most_repetitive = C2.most_common(1)
    # print(h, l, "most_repetitive distance:", most_repetitive[1])
    plot_histogram_distance(C2, args.outfolder, h, l, "distance_distribution", bins=len(C2))

    du = get_distance_nonuniformity(C2)
    # w_corr = get_window_correlation(p2_sampled)
    d_max2 = get_clumping_metric(p2_sampled, 2)
    d_max3 = get_clumping_metric(p2_sampled, 3)
    d_max4 = get_clumping_metric(p2_sampled, 4)
    d_max5 = get_clumping_metric(p2_sampled, 5)
    d_max6_and_up = sum( [get_clumping_metric(p2_sampled, i) for i in range(6,10)])
    d_min_5 = round(get_d_min(p2_sampled, n = 5, wmax = args.wmax), 3)
    print("{},{},{},{},{},{},{},{},{},{},{}".format(h,l,unique_p2_sampled,max_p2_sampled, du, d_min_5, d_max2, d_max3, d_max4, d_max5, d_max6_and_up)) #, distance_nonuniformity,W_correlation)

    # plot_histogram(args.positions, args.outfolder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Evaluate sampling dispersity", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('positions', type=str,  default=False, help='Input positions file')
    parser.add_argument('outfolder', type=str,  default=False, help='Input positions file')
    parser.add_argument('--k', type=int,  default=20, help='Input positions file')
    parser.add_argument('--wmax', type=int,  default=100, help='Input positions file')

    args = parser.parse_args()
    mkdir_p(args.outfolder)

    main(args)


