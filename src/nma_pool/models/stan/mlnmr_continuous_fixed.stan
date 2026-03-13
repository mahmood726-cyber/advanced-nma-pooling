data {
  int<lower=1> N;
  int<lower=1> P;
  matrix[N, P] X;
  vector[N] y;
  matrix[N, N] L_V;
  real<lower=0> prior_scale;
}

parameters {
  vector[P] beta;
}

model {
  beta ~ normal(0, prior_scale);
  y ~ multi_normal_cholesky(X * beta, L_V);
}

