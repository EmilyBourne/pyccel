# coding: utf-8

from numpy import zeros
from numpy import dot

n = 10
a = zeros(shape=(10,10), dtype=float)
b = zeros(shape=(10,10), dtype=float)

#def gaussElimin(a,b):
#n = len(b)

m = n - 1
for k in range(0,m):
    p = k + 1
    for i in range(p,n):
        if a[i,k] <> 0.0:
            lam = a [i,k]/a[k,k]
#            a[i,k+1:n] = a[i,k+1:n] - lam*a[k,k+1:n]
#            b[i] = b[i] - lam*b[k]
#    for k in range(n-1,-1,-1):
#        b[k] = (b[k] - dot(a[k,k+1:n],b[k+1:n]))/a[k,k]
#return b
