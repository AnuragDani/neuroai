#!/usr/bin/env Rscript
# Fixture only. No dataset loader or Seurat/Signac support is claimed.
args <- commandArgs(trailingOnly = TRUE)
mode <- if (length(args)) args[[1]] else "valid"
if (!requireNamespace("Matrix", quietly = TRUE)) stop("NOT_RUN: Matrix absent")

validate <- function(object) {
  if (!identical(names(object), c("counts", "regions", "cells"))) stop("FIELDS")
  counts <- object$counts
  if (!inherits(counts, "dgCMatrix")) stop("SPARSE_CLASS")
  methods::validObject(counts)
  if (any(!is.finite(counts@x)) || any(counts@x < 0) ||
      any(counts@x != floor(counts@x))) stop("COUNTS")
  for (ids in dimnames(counts)) {
    if (is.null(ids) || anyNA(ids) || any(!nzchar(ids)) || anyDuplicated(ids)) stop("IDS")
  }
  if (!identical(rownames(counts), object$regions$id) ||
      !identical(colnames(counts), object$cells$id)) stop("ORDER")
  regions <- object$regions
  if (!identical(names(regions), c("id", "chromosome", "start", "end"))) stop("REGIONS")
  if (anyNA(regions) || any(!nzchar(regions$chromosome)) ||
      any(regions$start < 0) || any(regions$end <= regions$start) ||
      any(regions$start != floor(regions$start)) ||
      any(regions$end != floor(regions$end))) stop("INTERVALS")
  if (!identical(names(object$cells), c("id", "donor")) ||
      anyNA(object$cells) || any(!nzchar(object$cells$donor))) stop("DONORS")
  invisible(TRUE)
}

object <- list(
  counts = Matrix::sparseMatrix(i = c(1, 3, 2, 1), j = c(1, 1, 2, 4),
    x = c(2, 7, 1, 5), dims = c(3, 4),
    dimnames = list(c("chr1:0-10", "chr1:20-30", "chr2:5-9"),
      c("cell_a", "cell_b", "cell_c", "cell_d"))),
  regions = data.frame(id = c("chr1:0-10", "chr1:20-30", "chr2:5-9"),
    chromosome = c("chr1", "chr1", "chr2"), start = c(0L, 20L, 5L), end = c(10L, 30L, 9L)),
  cells = data.frame(id = c("cell_a", "cell_b", "cell_c", "cell_d"),
    donor = c("donor_1", "donor_1", "donor_2", "donor_2"))
)
if (mode == "bad_counts") object$counts@x[1] <- 0.5
if (mode == "bad_ids") colnames(object$counts)[2] <- colnames(object$counts)[1]
if (mode == "bad_fields") object$regions <- NULL
if (mode == "bad_intervals") object$regions$end[1] <- -1
if (!mode %in% c("valid", "bad_counts", "bad_ids", "bad_fields", "bad_intervals", "reuse")) stop("MODE")
validate(object)
output <- "/tmp/p22-fixture.rds"
if (mode == "reuse") file.create(output)
if (file.exists(output)) stop("OUTPUT_EXISTS")
saveRDS(object, output, compress = "gzip", version = 3)
stopifnot(file.info(output)$size <= 1048576)
restored <- readRDS(output)
validate(restored)
stopifnot(identical(object, restored))
cat("R_VERSION\t", as.character(getRversion()), "\n", sep = "")
cat("MATRIX_VERSION\t", as.character(utils::packageVersion("Matrix")), "\n", sep = "")
cat("CLASS\t", class(restored$counts), "\n", sep = "")
cat("FIXTURE_BYTES\t", file.info(output)$size, "\n", sep = "")
cat("FIXTURE_MD5\t", unname(tools::md5sum(output)), "\n", sep = "")
cat("ROWS\t", paste(rownames(restored$counts), collapse = ","), "\n", sep = "")
cat("COLUMNS\t", paste(colnames(restored$counts), collapse = ","), "\n", sep = "")
cat("DONORS\t", paste(restored$cells$donor, collapse = ","), "\n", sep = "")
entries <- summary(restored$counts)
for (n in seq_len(nrow(entries))) cat("ENTRY\t", entries$i[n], "\t", entries$j[n], "\t", entries$x[n], "\n", sep = "")
cat("SPARSE_ROUNDTRIP_PASS\nSCIENTIFIC_GATES_UNCHANGED\n")
