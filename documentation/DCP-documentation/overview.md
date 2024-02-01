# What is Distributed-CellProfiler?

**How do I run CellProfiler on Amazon?** Use Distributed-CellProfiler!

Distributed-CellProfiler is a series of scripts designed to help you run a Dockerized version of CellProfiler on [Amazon Web Services](https://aws.amazon.com/) (AWS) using AWS's file storage and computing systems.  
* Data is stored in S3 buckets.
* Software is run on "Spot Fleets" of computers (or instances) in the cloud.

## What is Docker?

Docker is a software platform that packages software into containers.
In a container is the software that you want to run as well as everything needed to run it (e.g. your software source code, operating system libraries, and dependencies).

Dockerizing a workflow has many benefits including
* Ease of use: Dockerized software doesn't require the user to install anything themselves.
* Reproducibility: You don't need to worry about results being affected by the version of your software or its dependencies being used as those are fixed.

## Why would I want to use this?

Using AWS allows you to create a flexible, on-demand computing infrastructure where you only have to pay for the resources you use.
This can give you access to far more computing power than you may have available at your home institution, which is great when you have large datasets to process.

Each piece of the infrastructure has to be added and configured separately, which can be time-consuming and confusing.

Distributed-CellProfiler tries to leverage the power of the former, while minimizing the problems of the latter.

## What do I need to have to run this?

Essentially all you need to run Distributed-CellProfiler is an AWS account and a terminal program; see our [page on getting set up](step_0_prep.md) for all the specific steps you'll need to take.

## Can I contribute code to Distributed-CellProfiler?

Feel free!  We're always looking for ways to improve.

## Who made this?

Distributed-CellProfiler is a project from the [Cimini Lab](https://cimini-lab.broadinstitute.org) in the Imaging Platform at the Broad Institute in Cambridge, MA, USA. It was initially developed in what is now the [Carpenter-Singh Lab](https://carpenter-singh-lab.broadinstitute.org).
