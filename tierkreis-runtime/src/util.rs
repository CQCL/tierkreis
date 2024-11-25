use futures::Future;
use std::pin::Pin;
use tokio::task::{JoinError, JoinHandle};

#[derive(Debug)]
pub struct JoinHandleWithDrop<R>(JoinHandle<R>);

impl<R> Future for JoinHandleWithDrop<R> {
    type Output = Result<R, JoinError>;

    fn poll(
        mut self: std::pin::Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
    ) -> std::task::Poll<Self::Output> {
        Pin::new(&mut self.as_mut().0).poll(cx)
    }
}

impl<R> Drop for JoinHandleWithDrop<R> {
    fn drop(&mut self) {
        self.abort()
    }
}

impl<R> From<JoinHandle<R>> for JoinHandleWithDrop<R> {
    fn from(handle: JoinHandle<R>) -> Self {
        Self(handle)
    }
}

impl<R> JoinHandleWithDrop<R> {
    pub fn abort(&self) {
        self.0.abort()
    }
}
