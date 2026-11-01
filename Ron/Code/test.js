async function loadPostWithAuthor(postId) {
  const post = await fetchPost(postId);
  const author = await fetchAuthor(post.authorId);
  return { post, author };
}
loadPostWithAuthor(1).then(result => {
  console.log(result);
} );