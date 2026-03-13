data {
  int<lower=1> N;
  int<lower=1> P;
  matrix[N, P] X;
  vector[N] y;
  matrix[N, N] L_M;
  vector<lower=0>[P] prior_sd;
}

parameters {
  vector[P] beta;
}

model {
  for (p in 1:P) {
    beta[p] ~ normal(0, prior_sd[p]);
  }
  y ~ multi_normal_cholesky(X * beta, L_M);
}
